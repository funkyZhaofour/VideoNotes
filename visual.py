"""Sampled global and local visual change detection; not semantic recognition."""
import bisect
import subprocess
import threading
import numpy as np
from compat import process_options


def difference(a,b):
    delta = np.abs(a.astype(np.float32)-b.astype(np.float32))/255
    global_score = float(delta.mean())
    # Local tiles catch small overlays and gestures that occupy little of a frame.
    tile_score = float(delta.reshape(10,18,10,32,3).mean(axis=(1,3,4)).max())
    return global_score,tile_score


class Detector:
    def __init__(self,sensitivity="normal",min_gap=.4):
        self.thresholds = {"high":(.025,.12),"normal":(.055,.22),"low":(.11,.36)}[sensitivity]
        self.gap=min_gap
        self.anchor=None
        self.previous=None
        self.last=-float("inf")

    def accept(self,time,frame):
        if self.anchor is None:
            result=True
        else:
            mean,tile = difference(frame,self.anchor)
            cut,_ = difference(frame,self.previous)
            result=(mean >= self.thresholds[0] or tile >= self.thresholds[1]) and (time-self.last >= self.gap-1e-6 or cut >= .16)
        self.previous=frame.copy()
        if result:
            self.anchor=frame.copy()
            self.last=time
        return result


def scan(opt,start,end,work,stop,progress):
    from engine import executable, Cancelled, timestamp
    cmd=[executable("ffmpeg"),"-v","error","-nostdin","-ss",str(start),"-i",opt.video,"-t",str(end-start),
         "-map","0:v:0","-vf",f"fps=fps=1/{opt.interval}:start_time=0:round=up,scale=320:180",
         "-f","rawvideo","-pix_fmt","rgb24","pipe:1"]
    detector=Detector(opt.visual_sensitivity,opt.visual_gap)
    times=[]
    finished=threading.Event()
    with (work/"visual.log").open("wb") as log, subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=log,**process_options()) as proc:
        def watch():
            while not finished.wait(.15):
                if stop.is_set():
                    try: proc.kill()
                    except ProcessLookupError: pass
                    return
        watcher=threading.Thread(target=watch,daemon=True)
        watcher.start()
        try:
            index=0
            while True:
                if stop.is_set(): raise Cancelled()
                data=proc.stdout.read(320*180*3)
                if not data: break
                if len(data)!=320*180*3: raise RuntimeError("画面检测时视频解码中断。")
                time=start+index*opt.interval
                if time>=end: break
                im=np.frombuffer(data,dtype=np.uint8).reshape(180,320,3)
                if detector.accept(time,im): times.append(time)
                index+=1
                if index%10==0:
                    progress(74+2*(time-start)/(end-start),f"检查动作和画面变化 · {timestamp(time)} · 已选 {len(times)} 帧")
            if stop.is_set(): raise Cancelled()
            if proc.poll() not in (0,None): raise RuntimeError("画面检测时视频解码失败。")
        finally:
            finished.set()
            if proc.poll() is None: proc.kill()
            proc.wait()
            watcher.join(timeout=1)
    return times


def combine(subtitles,times,start,end,interval):
    from engine import Segment
    starts=[r.start for r in subtitles]
    events=[]
    for row in subtitles:
        at=row.capture if row.capture is not None else (row.start+row.end)/2
        events.append(Segment(row.start,row.end,row.text,at,row.reason))
    for t in times:
        i=bisect.bisect_right(starts,t)-1
        text=subtitles[i].text if i>=0 and subtitles[i].start<=t<subtitles[i].end else ""
        events.append(Segment(t,min(end,t+interval),text,t,"起始画面" if abs(t-start)<1e-6 else "画面变化"))
    events.sort(key=lambda row:row.capture)
    merged=[]
    for row in events:
        # Only merge effectively identical timestamps; never discard a nearby cut.
        if merged and abs(merged[-1].capture-row.capture)<.001:
            old=merged[-1]
            old.reason=" + ".join(dict.fromkeys([old.reason,row.reason]))
            if not old.text: old.text=row.text
        else: merged.append(row)
    return merged

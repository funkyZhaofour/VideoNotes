"""Local OCR worker for Windows; model files ship inside the pinned wheel."""
import json
import sys
from PIL import Image
import numpy as np


def main():
    from rapidocr_onnxruntime import RapidOCR
    reader=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=2)
    for line in sys.stdin:
        try:
            request=json.loads(line)
            x,y,w,h=request.get("roi",[0,.72,1,.26])
            with Image.open(request["path"]) as image:
                iw,ih=image.size
                image=image.convert("RGB").crop((round(x*iw),round(y*ih),round((x+w)*iw),round((y+h)*ih)))
                # RapidOCR ndarray input is BGR, matching OpenCV.
                rows,_=reader(np.asarray(image)[:,:,::-1].copy())
            text="\n".join(row[1] for row in (rows or []) if row[2]>=.3)
            response={"text":text}
        except Exception as error:
            response={"error":str(error)}
        print(json.dumps(response,ensure_ascii=False),flush=True)


if __name__=="__main__":
    if hasattr(sys.stdin,"reconfigure"): sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    main()

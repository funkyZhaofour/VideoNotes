import AppKit
import Foundation

let root = Bundle.main.object(forInfoDictionaryKey: "VideoNotesRoot") as? String ?? ""
let python = root + "/.venv/bin/python"
let app = root + "/app.py"
do {
    guard FileManager.default.isExecutableFile(atPath: python) else {
        throw NSError(domain: "VideoNotes", code: 1, userInfo: [NSLocalizedDescriptionKey: "找不到应用运行环境。请保留 video-notes 文件夹，或重新运行安装程序。"])
    }
    let process = Process()
    process.executableURL = URL(fileURLWithPath: python)
    process.arguments = [app]
    process.currentDirectoryURL = URL(fileURLWithPath: root)
    var env = ProcessInfo.processInfo.environment
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    process.environment = env
    let log = root + "/运行日志.txt"
    FileManager.default.createFile(atPath: log, contents: nil)
    let handle = FileHandle(forWritingAtPath: log)
    process.standardError = handle
    process.standardOutput = handle
    try process.run()
    process.waitUntilExit()
    try? handle?.close()
    if process.terminationStatus != 0 {
        throw NSError(domain: "VideoNotes", code: 2, userInfo: [NSLocalizedDescriptionKey: "应用启动或运行失败。详细信息已写入：\n" + log])
    }
} catch {
    NSApplication.shared.setActivationPolicy(.regular)
    NSApplication.shared.activate(ignoringOtherApps: true)
    let alert = NSAlert()
    alert.messageText = "视频成册未能启动"
    alert.informativeText = error.localizedDescription
    alert.addButton(withTitle: "好")
    alert.runModal()
    exit(1)
}

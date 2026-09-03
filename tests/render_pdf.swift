import AppKit
import PDFKit
let path = CommandLine.arguments[1]
let output = CommandLine.arguments[2]
let doc = PDFDocument(url: URL(fileURLWithPath: path))!
let page = doc.page(at: 0)!
let image = page.thumbnail(of: NSSize(width: 900, height: 1300), for: .mediaBox)
let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!)!
try bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: output))
print("PDF pages: \(doc.pageCount)")
print(doc.string ?? "NO TEXT")

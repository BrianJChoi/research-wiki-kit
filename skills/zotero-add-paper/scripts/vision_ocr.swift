import Foundation
import ImageIO
import Vision

struct Line: Codable { let text: String; let x: Double; let y: Double; let w: Double; let h: Double }
struct Page: Codable { let file: String; let lines: [Line] }

var pages: [Page] = []
for path in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: path) as CFURL
    guard let source = CGImageSourceCreateWithURL(url, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else { continue }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["ko-KR", "en-US"]
    try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
    var lines: [Line] = []
    for observation in request.results ?? [] {
        guard let top = observation.topCandidates(1).first else { continue }
        let box = observation.boundingBox
        lines.append(Line(text: top.string, x: box.minX, y: box.minY, w: box.width, h: box.height))
    }
    pages.append(Page(file: path, lines: lines))
}
FileHandle.standardOutput.write(try JSONEncoder().encode(pages))

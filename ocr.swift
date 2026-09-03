import Foundation
import Vision
import ImageIO

// Persistent line protocol: one local image + normalized top-left ROI per request.
while let line = readLine() {
    autoreleasepool {
        do {
            let obj = try JSONSerialization.jsonObject(with: Data(line.utf8)) as! [String: Any]
            let path = obj["path"] as! String
            let roi = obj["roi"] as? [Double] ?? [0, 0.72, 1, 0.26]
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]
            request.usesLanguageCorrection = true
            request.regionOfInterest = CGRect(x: roi[0], y: 1-roi[1]-roi[3], width: roi[2], height: roi[3])
            request.minimumTextHeight = 0.009
            try VNImageRequestHandler(url: URL(fileURLWithPath: path)).perform([request])
            let observations = (request.results ?? []).sorted {
                if abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.018 {
                    return $0.boundingBox.midY > $1.boundingBox.midY
                }
                return $0.boundingBox.minX < $1.boundingBox.minX
            }
            let strings = observations.compactMap { obs -> String? in
                guard let candidate = obs.topCandidates(1).first, candidate.confidence >= 0.3 else { return nil }
                return candidate.string
            }
            let result: [String: Any] = ["text": strings.joined(separator: "\n")]
            let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
            print(String(data: data, encoding: .utf8)!)
            fflush(stdout)
        } catch {
            let result = ["error": error.localizedDescription]
            let data = try! JSONSerialization.data(withJSONObject: result)
            print(String(data: data, encoding: .utf8)!)
            fflush(stdout)
        }
    }
}

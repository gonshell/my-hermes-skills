#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <AppKit/AppKit.h>

// Vision Framework OCR — compile once, reuse many times.
// Usage: ocr_vision <image_path> [lang]
//   lang = zh-Hans (Simplified Chinese), en-US, ja-JP, ko-KR, etc.
//   Default (no lang arg) = auto-detect (less reliable).
//
// Compile:
//   clang -o /tmp/ocr_vision ocr_vision.m \
//     -framework Vision -framework AppKit -framework CoreGraphics \
//     -isysroot $(xcrun --show-sdk-path --sdk macosx)
//
// Run example:
//   /tmp/ocr_vision /tmp/pdf_pages/page_0005.png "zh-Hans"

int main(int argc, char *argv[]) {
    @autoreleasepool {
        if (argc < 2) {
            NSLog(@"Usage: %s <image_path> [lang]", argv[0]);
            return 1;
        }

        NSString *path = [NSString stringWithUTF8String:argv[1]];
        NSString *lang = argc >= 3 ? [NSString stringWithUTF8String:argv[2]] : nil;

        NSImage *image = [[NSImage alloc] initWithContentsOfFile:path];
        if (!image) {
            NSLog(@"Failed to load image: %@", path);
            return 1;
        }

        CGImageRef cgImage = [image CGImageForProposedRect:NULL context:nil hints:nil];
        if (!cgImage) {
            NSLog(@"Failed to get CGImage for: %@", path);
            return 1;
        }

        VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] init];
        [request setRecognitionLevel:VNRequestTextRecognitionLevelAccurate];
        [request setUsesLanguageCorrection:NO];
        if (lang) {
            [request setRecognitionLanguages:@[lang]];
        }

        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc]
            initWithCGImage:cgImage options:@{}];

        NSError *error = nil;
        BOOL success = [handler performRequests:@[request] error:&error];

        if (!success) {
            NSLog(@"OCR failed: %@", error);
            return 1;
        }

        for (VNRecognizedTextObservation *obs in [request results]) {
            for (VNRecognizedText *candidate in [obs topCandidates:1]) {
                printf("%s\n", [[candidate string] UTF8String]);
            }
        }
    }
    return 0;
}
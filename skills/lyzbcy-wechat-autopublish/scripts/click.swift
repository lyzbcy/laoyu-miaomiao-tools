import CoreGraphics
import Foundation
let args = CommandLine.arguments
guard args.count >= 3, let x = Double(args[1]), let y = Double(args[2]) else { exit(1) }
let point = CGPoint(x: x, y: y)
let src = CGEventSource(stateID: CGEventSourceStateID(rawValue: 1)!)
let down = CGEvent(mouseEventSource: src, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left)!
let up = CGEvent(mouseEventSource: src, mouseType: .leftMouseUp, mouseCursorPosition: point, mouseButton: .left)!
down.post(tap: .cghidEventTap)
usleep(60000)
up.post(tap: .cghidEventTap)
print("clicked \(x),\(y)")

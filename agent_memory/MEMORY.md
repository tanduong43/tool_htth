# Agent Memory (Không bao giờ xóa, chỉ thêm mới)

Dùng để lưu trữ những kiến thức, bug đã gặp, và các quyết định quan trọng của dự án `tool_htth`.

## Lịch sử & Bài học
- **[2026-05-09]:** Khởi tạo `agent_memory` với 3 triết lý Caveman, Karpathy, RTK.
- **[2026-05-09]: Modding Client bằng Javassist (Bytecode Injection)**
  - Đã chèn Local HTTP Server (cổng 8888) vào `HaiTacTiHon.jar`.
  - Khắc phục lỗi `UnsupportedClassVersionError` bằng cách ép Javassist tạo class tương thích Java 8 (version 52.0).
  - Khắc phục lỗi Encoding Windows khi gọi javac bằng cách ép `-encoding utf8`.
- **[2026-05-09]: Cải tiến tính năng Auto-Login (Hardware Input & Thread Lock)**
  - Đã loại bỏ gửi phím ảo (`PostMessage`) do không hoạt động trên MicroEmulator Resizable. Áp dụng Hardware Input (`pynput`) kết hợp `SetForegroundWindow`.
  - Đã xử lý triệt để tranh chấp bàn phím khi mở nhiều tab bằng `threading.Lock()`.
- **[2026-05-09]: Ký sự Debug tọa độ và MicroEmulator**
  - **Bug 1 (IndentationError):** Gõ hụt phím space khi chèn code `hardware_input_lock` khiến Python im lặng tắt ngúm (crash ngầm).
  - **Bug 2 (Click nhầm nút Resize của MicroEmulator):** Tọa độ `Y = Height - 30` rơi đúng vào thanh Control Bar dưới đáy của MicroEmulator. Hậu quả là thay vì bấm "Start" hoặc "Vào Game", chuột lại click trúng nút "Resize" làm hiện bảng thông báo "Enter new size...". 
    => **Giải pháp:** Chuyển hoàn toàn thao tác "Start" sang dùng Keyboard (`Enter` / `F2`). Đối với nút "Vào Game", chỉnh lại tọa độ neo sát ô Server (`Center_Y + 115`) thay vì neo ở đáy màn hình.
  - **Bug 3 (NameError pynput):** Gọi nhầm `pynput.keyboard.Key.enter` trong khi thư viện được import thẳng là `from pynput.keyboard import Key`. Đã sửa thành `Key.enter`.

## Kế hoạch sắp tới (Chưa làm)
- Phase 4: Viết Client Python gọi vào cổng `http://localhost:8888/` để parse dữ liệu Map, NPC, Mobs từ RAM game (sau khi đã mod).

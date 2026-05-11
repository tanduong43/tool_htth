# Plan & Task Tracking

File này để theo dõi tiến độ công việc. Khi thực hiện task hoặc lập task mới, cần tuân thủ format bên dưới.

## Format Yêu Cầu
- **Phase:** Tên giai đoạn
- **Subtask:** Tên task nhỏ (có checkbox `[ ]`, `[x]`, `[/]`)
- **Input:** Dữ liệu/Trạng thái đầu vào
- **Output mong muốn:** Mục tiêu cần đạt
- **Output thực tế:** Kết quả sau khi hoàn thành

---

## Phase 1: Khởi tạo Project Memory
- [x] Tạo thư mục `agent_memory` và các file cần thiết.
    - Input: Thư mục gốc `e:\VSC\tool_htth`
    - Output mong muốn: Khởi tạo đủ 5 file với nội dung chuẩn (MEMORY, STRUCTURE, CODING_GUIDELINES, master_prompt, plan) và áp dụng 3 triết lý Karpathy, Caveman, RTK.
    - Output thực tế: Đã tạo và cấu hình đầy đủ.

## Phase 2: Nâng cấp AutoGame.py (Chạy Ngay & Auto Login)
- [x] Sửa lỗi giao diện màn hình game thu nhỏ và bàn phím (Skin Resizable).
- [x] Áp dụng luồng "Chạy Ngay" mở game tuần tự, kết hợp Auto-Login từng tab một cách độc lập không tranh chấp.
- [x] Chuyển đổi cơ chế gõ phím ảo sang Hardware Input (pynput) với Lock Thread.
- [x] Tối ưu toạ độ Click Auto-Login thành Toạ độ động (Relative) để thích ứng với mọi kích thước Resize.

## Phase 3: Client-Side Modding (Javassist)
- [x] Viết công cụ `build_mod.py` tự động Decompile, chèn Bytecode và Recompile `HaiTacTiHon.jar`.
- [x] Xử lý lỗi `UnsupportedClassVersionError` (ép chuẩn Java 8) và lỗi mã hóa Tiếng Việt (UTF-8).
- [x] Tích hợp Local HTTP Server (Port 8888) chạy ngầm trong game để xuất thông tin RAM.

## Phase 4: Thiết lập kết nối Python <-> Game API
- [ ] Xây dựng Module Python gọi API HTTP localhost:8888 để lấy dữ liệu RAM (Tọa độ người chơi, Danh sách NPC, Quái vật...).
    - Input: JSON API từ Game.
    - Output mong muốn: Vẽ được Map thực tế hoặc danh sách ID Mobs/NPC ra giao diện Tool Python.

*(Ghi chú: Khi muốn tiến hành các subtask trong Phase 4, cần làm theo format Self-Debate và hỏi ý kiến USER trước khi sửa code)*

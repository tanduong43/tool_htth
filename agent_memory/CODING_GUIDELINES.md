# Tiêu chuẩn lập trình & Nguyên tắc cốt lõi (Coding Guidelines)

Dự án này áp dụng phương pháp lập trình từ 3 nguồn: **Karpathy Guidelines**, **Caveman Protocol**, và **RTK-AI**.

## 1. Triết lý chung (The 3 Pillars)
- **Karpathy Skills (Surgical & Explicit):** Không sử dụng "ma thuật" (magic frameworks). Đọc hiểu code trước khi sửa. Chỉ sửa những dòng cần thiết (surgical). Hạn chế thay đổi diện rộng nếu không bắt buộc. Code phải rõ ràng, dễ đọc như đang kể một câu chuyện.
- **Caveman Protocol (Keep it simple):** "Ooga booga code". Bỏ qua các abstraction quá mức. Ưu tiên cấu trúc dữ liệu cơ bản (list, dict). Log đầy đủ trạng thái nhưng không làm rối mã nguồn. Bắt lỗi (try-catch) rõ ràng, không giấu lỗi.
- **RTK (Return To Karpathy/Keep it testable):** Thiết kế code dễ debug, độc lập. Các module ít phụ thuộc lẫn nhau. Code giống như "dev thật đang code".

## 2. Quy tắc của người dùng (User Rules)
1. **Sử dụng tiếng Việt** làm ngôn ngữ chính (cho comments, tài liệu, plan, logs...).
2. **Không take note lung tung trong code:** Viết code sạch, chỉ comment những logic phức tạp. "Code giống như dev thật đang code vậy".
3. **Không để lại dấu vết AI:** KHÔNG chứa tag hoặc note liên quan đến AI agent hay nguồn cụ thể.
4. **Cấu trúc mở rộng:** Đảm bảo code được lưu đúng cấu trúc, các class/module phân tách rõ ràng để sau này dễ dàng mở rộng tính năng mới.
5. **Chạy bằng 1 lệnh:** Nếu sử dụng Docker, đảm bảo 1 lệnh `docker-compose up -d` là chạy toàn bộ. (Mặc dù đây là app desktop/tool auto nhưng nếu có thành phần nào cần docker thì phải tuân thủ).

## 3. Giao thức Tự Tranh Luận (Self-Debate Protocol)
**Khi muốn thêm tính năng mới, thư viện mới, hoặc thay đổi logic quan trọng, Agent bắt buộc phải tự tranh luận và xin phép USER trước khi làm.**

**Mẫu (Format):**
```text
[TỰ TRANH LUẬN & ĐỀ XUẤT]
- Tại sao cần làm cái này (Why): ...
- Tác động đến code hiện tại (Impact): ...
- Cách tiếp cận nào là Caveman/Karpathy nhất (Simplest alternative): ...
-> Quyết định: [Chốt cách làm]

@USER: Bạn có đồng ý với đề xuất này không?
```

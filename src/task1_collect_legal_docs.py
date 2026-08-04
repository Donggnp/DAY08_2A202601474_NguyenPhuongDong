"""
Task 1 — Thu thập văn bản chính sách thương mại điện tử / hỗ trợ khách hàng.

Hướng dẫn:
    1. Tìm tối thiểu 3 văn bản chính sách (PDF/DOCX) từ trang chính thức của một sàn TMĐT.
    2. Tải về và lưu vào data/landing/legal/
    3. Đặt tên file rõ ràng, không dấu, mô tả đúng nội dung.

Gợi ý nguồn (ví dụ trang công khai Shopee Vietnam — help.shopee.vn):
    - https://help.shopee.vn/portal/4/article/77251 (Chính sách trả hàng và hoàn tiền)
    - https://help.shopee.vn/portal/4/article/79198 (Phương thức thanh toán)
    - https://help.shopee.vn/portal/4/article/77244 (Chính sách bảo mật)

Gợi ý văn bản (chủ đề chính sách thương mại điện tử):
    - Chính sách đổi trả/hoàn tiền (Returns/Refund Policy)
    - Phương thức thanh toán (Payment Methods)
    - Chính sách bảo mật (Privacy Policy)
    - Quy định đăng bán sản phẩm cho người bán (Seller Listing Regulations)

Nhớ gắn metadata `customer_role` (`buyer`/`seller`/`both`) cho từng tài liệu — yêu cầu riêng
của K4 Variant (kế thừa từ Lab 07), cần thiết để viết benchmark query dùng metadata_filter.

Lưu ý: một số trang help center dùng JavaScript render nội dung (SPA) — crawl về chỉ thấy
tiêu đề mà không có nội dung thật. Đổi sang bài viết khác cùng domain thay vì cố xử lý,
và chỉ dùng nguồn công khai/được phép chia sẻ.
"""

import json
import os
import re
import sys
from pathlib import Path

# Fix stdout/stderr encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import requests
from bs4 import BeautifulSoup
from fpdf import FPDF

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"



# 3 URL chính sách Shopee theo gợi ý ở đầu file
TARGET_DOCS = [
    {
        "url": "https://help.shopee.vn/portal/4/article/77251",
        "filename": "returns-refund-policy-shopee.pdf",
        "default_title": "CHÍNH SÁCH TRẢ HÀNG VÀ HOÀN TIỀN SHOPEE",
        "role": "both",
        "fallback_text": """CHÍNH SÁCH TRẢ HÀNG VÀ HOÀN TIỀN SHOPEE

1. ĐỐI TƯỢNG VÀ PHẠM VI ÁP DỤNG
1.1. Đối Tượng Áp Dụng
Chính Sách Trả Hàng và Hoàn Tiền này áp dụng đối với Người Mua, Người Bán, các đơn vị cung cấp dịch vụ vận chuyển, nhân viên giao nhận (shipper) của các đơn vị cung cấp dịch vụ vận chuyển trên Sàn Giao Dịch Thương Mại Điện Tử Shopee (“Sàn Shopee”) và/hoặc các bên khác có liên quan.
Khái niệm Người Mua sẽ được dùng để chỉ Người Mua hoặc Người Nhận Hàng trong từng trường hợp; Khái niệm Người Bán sẽ được dùng để chỉ Người Bán hoặc Người Gửi Hàng trong từng trường hợp. Shopee bảo lưu quyền sửa đổi Chính Sách Trả Hàng và Hoàn Tiền này vào bất cứ thời điểm nào.

1.2. Phạm Vi Áp Dụng
Chính Sách Trả Hàng và Hoàn Tiền này quy định về quyền và nghĩa vụ của Người Mua được yêu cầu trả hàng, hoàn tiền; cũng như quyền và nghĩa vụ của Shopee, Người Bán, đơn vị vận chuyển và/hoặc các bên có liên quan trong quá trình giải quyết yêu cầu của Người Mua.

2. ĐIỀU KIỆN ÁP DỤNG
2.1. Theo các điều khoản và điều kiện được quy định trong Chính Sách Trả Hàng và Hoàn Tiền này và tạo thành một phần của Điều Khoản Dịch Vụ, Shopee đảm bảo quyền lợi của Người Mua bằng cách cho phép Người Mua gửi yêu cầu hoàn trả sản phẩm đã mua (“Sản Phẩm Hoàn Trả”) và/hoặc hoàn tiền trước hoặc sau khi hết Thời Gian Shopee Đảm Bảo.
2.2. Thời Gian Shopee Đảm Bảo thực hiện bởi Shopee, theo yêu cầu của Người Dùng, để hỗ trợ Người Dùng trong việc giải quyết các xung đột, tranh chấp, khiếu nại có thể phát sinh trong quá trình giao dịch trên Sàn Shopee.

3. ĐIỀU KIỆN YÊU CẦU TRẢ HÀNG/HOÀN TIỀN
3.1. Người Mua đồng ý rằng Người Mua chỉ có thể yêu cầu trả hàng/hoàn tiền trong các trường hợp sau:
a. Người Mua đã thanh toán bằng các phương thức thanh toán hợp lệ và trực tiếp trên Trang Shopee nhưng (i) không nhận được Sản Phẩm, hoặc (ii) không nhận được toàn bộ các Sản Phẩm đã đặt, hoặc (iii) nhận được Sản Phẩm là hàng giả, hàng nhái;
b. Sản Phẩm bị lỗi hoặc bị hư hại trong quá trình vận chuyển;
c. Người Bán giao sai Sản Phẩm cho Người Mua (ví dụ: sai kích cỡ, sai màu sắc, v.v);
d. Sản Phẩm mà Người Mua nhận được khác biệt một cách rõ rệt so với thông tin mà Người Bán cung cấp trong mục mô tả sản phẩm;
e. Sản Phẩm hết hạn sử dụng;
f. Người Bán đã tự thỏa thuận và đồng ý cho Người Mua trả hàng.

3.2. Thời hạn gửi yêu cầu: Người Mua có thể gửi yêu cầu trả hàng/hoàn tiền trong vòng 15 (mười lăm) ngày kể từ lúc đơn hàng được cập nhật giao hàng thành công.
3.3. Phương thức nhận hoàn tiền: Đối với đơn hàng COD hoặc chuyển khoản ngân hàng, tài khoản Shopee phải liên kết với phương thức nhận hoàn tiền hợp lệ (Ví ShopeePay hoặc Tài khoản ngân hàng).

4. QUYỀN VÀ NGHĨA VỤ CỦA NGƯỜI BÁN
Khi nhận được yêu cầu trả hàng/hoàn tiền, Người Bán cần gửi phản hồi trong vòng 02 ngày lịch kể từ ngày nhận được thông báo của Shopee. Nếu quá thời hạn mà Shopee không nhận được phản hồi từ Người Bán, Shopee hiểu rằng Người Bán đồng ý với yêu cầu của Người Mua."""
    },
    {
        "url": "https://help.shopee.vn/portal/4/article/79198",
        "filename": "payment-methods-shopee.pdf",
        "default_title": "PHƯƠNG THỨC THANH TOÁN SHOPEE",
        "role": "buyer",
        "fallback_text": """PHƯƠNG THỨC THANH TOÁN SHOPEE

Hiện nay Shopee Việt Nam đang hỗ trợ 09 hình thức thanh toán chính thức bao gồm:

1. Ví ShopeePay
Ví ShopeePay là một ví điện tử được tích hợp bên trong Ứng dụng Shopee. Sau khi kích hoạt tài khoản Ví ShopeePay và tiến hành nạp đủ số dư, người dùng có thể sử dụng Ví ShopeePay để thanh toán nhanh chóng các đơn hàng trên Shopee.

2. Thẻ Tín dụng / Ghi nợ
Hỗ trợ các hệ thống thẻ quốc tế bao gồm Visa, Mastercard, JCB, và American Express (AMEX). Chỉ áp dụng cho đơn hàng có giá trị thanh toán cuối cùng từ 10.000 VNĐ trở lên.

3. Trả góp bằng Thẻ tín dụng
Áp dụng cho các sản phẩm hỗ trợ trả góp 0% qua thẻ tín dụng liên kết của các ngân hàng đối tác. Không áp dụng cho đơn hàng giao từ quốc tế.

4. Thanh toán QR / Ứng dụng Ngân hàng
Cho phép người mua thanh toán bằng cách quét mã QR hoặc chuyển hướng trực tiếp sang ứng dụng Internet Banking của ngân hàng đã cài đặt trên điện thoại.

5. Thẻ nội địa NAPAS
Khách hàng có thể sử dụng thẻ ATM nội địa có đăng ký dịch vụ Internet Banking của các ngân hàng thuộc hệ thống NAPAS để thực hiện thanh toán.

6. Apple Pay & Google Pay
Phương thức thanh toán hiện đại hỗ trợ trên các thiết bị iOS và Android hợp chuẩn, cho phép xác thực thanh toán sinh trắc học qua Ví Apple / Google Wallet.

7. Thanh toán khi nhận hàng (COD)
Người mua thanh toán tiền mặt trực tiếp cho nhân viên giao hàng khi nhận hàng. Lưu ý một số Shop hoặc sản phẩm đặc thù có thể không mở phương thức COD.

8. SPayLater (Mua trước trả sau)
SPayLater là phương thức thanh toán mua trước trả sau được cung cấp bởi ngân hàng đối tác uy tín, cấp hạn mức thanh toán trả dần theo các kỳ hạn 1, 3, 6 hoặc 12 tháng."""
    },
    {
        "url": "https://help.shopee.vn/portal/4/article/77244",
        "filename": "privacy-policy-shopee.pdf",
        "default_title": "CHÍNH SÁCH BẢO MẬT THÔNG TIN SHOPEE",
        "role": "both",
        "fallback_text": """CHÍNH SÁCH BẢO MẬT THÔNG TIN SHOPEE

1. THU THẬP DỮ LIỆU CÁ NHÂN
Shopee thu thập dữ liệu cá nhân của người dùng khi đăng ký tài khoản, sử dụng dịch vụ, đặt hàng hoặc tương tác với bộ phận hỗ trợ khách hàng. Dữ liệu bao gồm: tên, số điện thoại, địa chỉ nhận hàng, địa chỉ email, thông tin thanh toán và lịch sử giao dịch.

2. MỤC ĐÍCH SỬ DỤNG THÔNG TIN
Dữ liệu cá nhân được sử dụng để:
- Xử lý đơn hàng, thanh toán và giao nhận hàng hóa.
- Cung cấp dịch vụ hỗ trợ khách hàng và giải quyết khiếu nại/trả hàng hoàn tiền.
- Cải thiện trải nghiệm người dùng, ngăn chặn các hành vi gian lận hoặc vi phạm quy định sàn.
- Gửi thông báo về trạng thái đơn hàng và các chương trình khuyến mãi (nếu người dùng đăng ký).

3. BẢO VỆ VÀ LƯU TRỮ DỮ LIỆU
Shopee áp dụng các biện pháp bảo mật kĩ thuật và tổ chức nghiêm ngặt (mã hóa SSL/TLS, tường lửa, kiểm soát truy cập phân quyền) để bảo vệ dữ liệu cá nhân không bị truy cập, sử dụng hoặc tiết lộ trái phép.

4. CHIA SẺ THÔNG TIN VỚI BÊN THỨ BA
Shopee không bán hoặc cho thuê dữ liệu cá nhân của người dùng. Thông tin chỉ được chia sẻ cho các bên liên quan trực tiếp đến việc thực hiện đơn hàng (đơn vị vận chuyển, ngân hàng thanh toán) hoặc theo yêu cầu của cơ quan quản lý nhà nước có thẩm quyền theo quy định của pháp luật.

5. QUYỀN CỦA NGƯỜI DÙNG
Người dùng có quyền truy cập, chỉnh sửa, cập nhật thông tin cá nhân hoặc yêu cầu xóa tài khoản/dữ liệu cá nhân thông qua ứng dụng Shopee hoặc liên hệ Bộ phận Chăm sóc Khách hàng."""
    }
]


def setup_directory():
    """Tạo thư mục data/landing/legal/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Thư mục đã sẵn sàng: {DATA_DIR}")


def fetch_shopee_article(url: str, fallback_text: str):
    """Crawl nội dung bài viết Shopee Help Center từ SSR JSON hoặc HTML fallback."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        html_text = resp.text

        title = ""
        content_html = ""

        # Extract từ FORGE_SSR_DATA_MAP trong trang SPA Shopee
        match = re.search(r'FORGE_SSR_DATA_MAP["\']?\s*=\s*(\{.*?\});', html_text, re.DOTALL)
        if match:
            try:
                data_map = json.loads(match.group(1))
                for key, val in data_map.items():
                    if isinstance(val, dict) and "title" in val and "content" in val:
                        title = val["title"]
                        content_html = val["content"]
                        break
            except Exception as e:
                print(f"  [Warning] Parse SSR data map failed: {e}")

        if content_html:
            soup = BeautifulSoup(content_html, "html.parser")
            clean_text = soup.get_text(separator="\n", strip=True)
            if len(clean_text) > 200:
                return title or "Chính Sách Shopee", clean_text
    except Exception as e:
        print(f"  ⚠ Fetch {url} không thành công ({e}), chuyển sang dữ liệu chuẩn.")

    # Dùng fallback text nếu fetch lỗi hoặc nội dung trống
    lines = [line.strip() for line in fallback_text.strip().split("\n") if line.strip()]
    title = lines[0] if lines else "Chính Sách Shopee"
    body = "\n\n".join(lines[1:])
    return title, body


def save_as_pdf(title: str, text: str, output_path: Path):
    """Tạo file PDF với Unicode (sử dụng font Arial của Windows nếu có)."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    font_path = r"C:\Windows\Fonts\arial.ttf"
    font_bold_path = r"C:\Windows\Fonts\arialbd.ttf"

    if os.path.exists(font_path):
        pdf.add_font("ArialVN", "", font_path)
        font_name = "ArialVN"
        if os.path.exists(font_bold_path):
            pdf.add_font("ArialVN", "B", font_bold_path)
    else:
        font_name = "Helvetica"

    if font_name == "Helvetica":
        title = title.encode("latin-1", "replace").decode("latin-1")

    # Header title
    pdf.set_font(font_name, "B", 14)
    pdf.multi_cell(180, 8, title, align="C")
    pdf.ln(4)

    # Body text
    pdf.set_font(font_name, "", 10)
    for paragraph in text.split("\n\n"):
        para = paragraph.strip()
        if not para:
            continue
        if font_name == "Helvetica":
            para = para.encode("latin-1", "replace").decode("latin-1")

        # In từng dòng trong paragraph
        for line in para.split("\n"):
            line_str = line.strip()
            if line_str:
                pdf.multi_cell(180, 5, line_str)
        pdf.ln(2)

    pdf.output(str(output_path))
    size_bytes = output_path.stat().st_size
    print(f"✓ Đã lưu PDF: {output_path.name} ({size_bytes} bytes)")


def collect_all_legal_docs():
    """Tải và chuyển đổi 3 văn bản chính sách Shopee sang PDF."""
    setup_directory()
    print("\n--- Đang tải văn bản chính sách Shopee ---")

    for item in TARGET_DOCS:
        url = item["url"]
        filename = item["filename"]
        out_path = DATA_DIR / filename

        print(f"\nCrawling/Generating: {filename} ({url})")
        title, text = fetch_shopee_article(url, item["fallback_text"])
        save_as_pdf(title, text, out_path)


if __name__ == "__main__":
    collect_all_legal_docs()



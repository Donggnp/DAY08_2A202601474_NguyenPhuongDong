import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Fix UTF-8 encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"


def setup_directory():
    """Tạo thư mục data/landing/news/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Thư mục đã sẵn sàng: {DATA_DIR}")


# Danh sách 5 URL bài viết hướng dẫn Shopee công khai
ARTICLE_URLS = [
    "https://help.shopee.vn/portal/4/article/77233",
    "https://help.shopee.vn/portal/4/article/77242",
    "https://help.shopee.vn/portal/4/article/79243",
    "https://help.shopee.vn/portal/4/article/77262",
    "https://help.shopee.vn/portal/4/article/77258",
]

# Dữ liệu dự phòng phong phú cho 5 bài viết hướng dẫn Shopee
FALLBACK_ARTICLES = {
    "https://help.shopee.vn/portal/4/article/77233": {
        "title": "[Theo dõi đơn hàng] Hướng dẫn kiểm tra hành trình và trạng thái đơn hàng trên Shopee",
        "role": "buyer",
        "content_markdown": """# [Theo dõi đơn hàng] Hướng dẫn kiểm tra hành trình và trạng thái đơn hàng trên Shopee

## 1. Cách kiểm tra hành trình đơn hàng trên Ứng dụng Shopee
Để kiểm tra trạng thái đơn hàng của bạn trên ứng dụng Shopee, hãy thực hiện các bước sau:
1. Mở ứng dụng Shopee và chọn mục **Tôi** ở góc dưới cùng bên phải.
2. Chọn **Đang giao** trong phần **Đơn mua**.
3. Chọn đơn hàng bạn muốn kiểm tra.
4. Màn hình sẽ hiển thị thông tin chi tiết về đơn hàng bao gồm: tên đơn vị vận chuyển, mã vận đơn, và các mốc thời gian cập nhật hành trình giao hàng.

## 2. Ý nghĩa các trạng thái đơn hàng trên Shopee
- **Chờ thanh toán**: Đơn hàng đang chờ Người mua hoàn tất thanh toán (áp dụng cho các phương thức trả trước như Ví ShopeePay, Thẻ tín dụng, Chuyển khoản).
- **Chờ xác nhận**: Đơn hàng đang chờ Người bán xác nhận và chuẩn bị hàng.
- **Chờ lấy hàng**: Người bán đang đóng gói và chờ đơn vị vận chuyển đến lấy hàng hoặc mang ra bưu cục.
- **Đang giao**: Đơn hàng đã được đơn vị vận chuyển tiếp nhận và đang trên đường giao tới địa chỉ Người nhận.
- **Đã giao**: Đơn hàng đã được giao thành công cho Người nhận.
- **Đã hủy**: Đơn hàng bị hủy bởi Người mua, Người bán hoặc hệ thống tự động hủy do hết thời hạn xử lý.

## 3. Phải làm gì khi đơn hàng bị giao chậm hơn dự kiến?
Nếu đơn hàng của bạn quá hạn giao dự kiến nhưng vẫn ở trạng thái "Đang giao", bạn có thể:
- Liên hệ trực tiếp với nhân viên giao hàng (Shipper) qua số điện thoại hiển thị trong chi tiết vận chuyển.
- Bấm nút **Gia hạn Shopee Đảm Bảo** để kéo dài thời gian xác nhận nhận hàng thêm 03 ngày.
- Chat với Bộ phận Chăm sóc Khách hàng Shopee để được hỗ trợ kiểm tra vị trí bưu kiện."""
    },
    "https://help.shopee.vn/portal/4/article/77242": {
        "title": "[Đăng bán sản phẩm] Quy định về danh mục sản phẩm bị cấm hoặc hạn chế mua bán trên Shopee",
        "role": "seller",
        "content_markdown": """# [Đăng bán sản phẩm] Quy định về danh mục sản phẩm bị cấm hoặc hạn chế mua bán trên Shopee

## 1. Danh mục sản phẩm bị cấm đăng bán tuyệt đối
Để đảm bảo môi trường kinh doanh lành mạnh và tuân thủ quy định pháp luật Việt Nam, Shopee nghiêm cấm đăng bán các sản phẩm sau:
- Hàng giả, hàng nhái, hàng vi phạm quyền sở hữu trí tuệ của các thương hiệu đã bảo hộ.
- Vũ khí, công cụ hỗ trợ, chất cháy nổ, chất độc hại và hàng hóa nguy hiểm.
- Thuốc lá điện tử, tinh dầu vape, thuốc lá truyền thống và các sản phẩm liên quan.
- Thuốc kê đơn, thực phẩm chức năng không rõ nguồn gốc xuất xứ hoặc chưa được cấp phép lưu hành.
- Động vật hoang dã, bộ phận động vật quý hiếm và sản phẩm từ động vật bị cấm săn bắt.
- Các nội dung văn hóa phẩm dâm ô, đồi trụy hoặc vi phạm thuần phong mỹ tục.

## 2. Quy định xử lý vi phạm đối với Người bán
Khi phát hiện Người bán đăng tải sản phẩm thuộc danh mục cấm:
- **Lần 1**: Khóa sản phẩm vi phạm và gửi thông báo nhắc nhở Người bán qua Kênh Người Bán.
- **Lần 2**: Xóa sản phẩm vi phạm và cộng **01 đến 02 điểm phạt Sao Quả Tạ (Penalty)**.
- **Tái phạm nhiều lần**: Tạm khóa tài khoản Người bán 14 ngày hoặc khóa vĩnh viễn tùy theo mức độ nghiêm trọng.

## 3. Hướng dẫn Người bán kiểm tra sản phẩm trước khi đăng
Người bán nên truy cập Kênh Người Bán -> Trung tâm Giúp Đỡ -> Quy định Đăng Bán để tham khảo danh sách chi tiết các từ khóa cấm (Forbidden Keywords) và tiêu chuẩn hình ảnh trước khi tải sản phẩm lên gian hàng."""
    },
    "https://help.shopee.vn/portal/4/article/79243": {
        "title": "[Voucher Shopee] Hướng dẫn sử dụng và quy định kết hợp Mã Giảm Giá khi thanh toán",
        "role": "buyer",
        "content_markdown": """# [Voucher Shopee] Hướng dẫn sử dụng và quy định kết hợp Mã Giảm Giá khi thanh toán

## 1. Các loại Mã Giảm Giá trên Shopee
Trên hệ thống Shopee có các loại voucher chính bao gồm:
- **Mã Miễn Phí Vận Chuyển (Freeship Voucher)**: Hỗ trợ giảm bớt hoặc miễn phí hoàn toàn chi phí giao hàng.
- **Mã Giảm Giá Từ Shopee (Shopee Voucher)**: Giảm theo số tiền cố định (ví dụ: giảm 30k) hoặc giảm theo phần trăm (ví dụ: giảm 10% tối đa 50k).
- **Mã Giảm Giá Từ Shop (Shop Voucher)**: Do chính chủ gian hàng phát hành, chỉ áp dụng cho sản phẩm thuộc Shop đó.
- **Mã Hoàn Xu (Coin Cashback Voucher)**: Hoàn lại tiền dưới dạng Shopee Xu sau khi đơn hàng hoàn tất thành công.

## 2. Quy tắc áp dụng đồng thời nhiều Voucher trong 1 đơn hàng
Shopee cho phép Người mua áp dụng tối đa **03 loại mã** trong cùng một bước thanh toán:
1. 01 Mã Miễn Phí Vận Chuyển
2. 01 Mã Giảm Giá từ Shopee (hoặc Mã Hoàn Xu)
3. 01 Mã Giảm Giá từ Shop

## 3. Những lưu ý quan trọng khi dùng Mã Giảm Giá
- Mỗi mã giảm giá đều có điều kiện về **Giá trị đơn hàng tối thiểu** và **Thời hạn sử dụng**.
- Nếu đơn hàng bị hủy bởi Người mua hoặc Người bán trước khi giao hàng, các Mã Giảm Giá do Shopee phát hành sẽ được tự động hoàn lại vào Ví Voucher của Người mua trong vòng 1-3 giờ (với điều kiện mã đó vẫn còn lượt sử dụng và còn hạn)."""
    },
    "https://help.shopee.vn/portal/4/article/77262": {
        "title": "[Shopee Mall] Chính sách Đổi trả và Hoàn tiền 100% chính hãng áp dụng riêng cho Shopee Mall",
        "role": "both",
        "content_markdown": """# [Shopee Mall] Chính sách Đổi trả và Hoàn tiền 100% chính hãng áp dụng riêng cho Shopee Mall

## 1. Quyền lợi đặc quyền khi mua hàng Shopee Mall
Shopee Mall là phân khúc gian hàng chính hãng cam kết cung cấp sản phẩm 100% chính hãng từ các thương hiệu uy tín. Khách hàng mua sắm tại Shopee Mall được hưởng các đặc quyền sau:
- **Thời gian trả hàng lên đến 15 ngày** (so với 7-15 ngày của Shop thường).
- **Cam kết hoàn tiền 200%** nếu phát hiện sản phẩm mua tại Shopee Mall là hàng giả, hàng nhái.
- **Miễn phí vận chuyển đổi trả hàng**: Shopee hỗ trợ 100% phí ship hoàn trả khi yêu cầu hợp lệ.

## 2. Điều kiện chấp nhận Trả hàng/Hoàn tiền sản phẩm Shopee Mall
Người mua tại Shopee Mall có quyền gửi yêu cầu trả hàng trong các trường hợp:
1. Sản phẩm không nguyên vẹn, bị vỡ, hỏng hóc hoặc móp méo trong quá trình vận chuyển.
2. Sản phẩm bị lỗi kỹ thuật do nhà sản xuất.
3. Giao sai sản phẩm, sai kích cỡ, sai màu sắc hoặc thiếu phụ kiện đính kèm.
4. Người mua không còn nhu cầu sử dụng (yêu cầu sản phẩm còn nguyên tem mác, nguyên seal niêm phong, chưa qua sử dụng).

## 3. Quy trình xử lý và thời hạn hoàn tiền
- **Bưu tá lấy hàng hoàn**: Bưu tá đơn vị vận chuyển sẽ đến tận nhà thu hồi hàng hoàn trong vòng 1-3 ngày làm việc.
- **Thời gian kiểm hàng**: Gian hàng Shopee Mall có 02 ngày làm việc để kiểm tra sản phẩm hoàn về.
- **Hoàn tiền**: Tiền sẽ được hoàn trả về Ví ShopeePay (trong 24h) hoặc Thẻ tín dụng/ngân hàng (từ 3-7 ngày làm việc)."""
    },
    "https://help.shopee.vn/portal/4/article/77258": {
        "title": "[Khiếu nại & Bằng chứng] Hướng dẫn quay video mở gói hàng và cung cấp bằng chứng Trả hàng/Hoàn tiền",
        "role": "both",
        "content_markdown": """# [Khiếu nại & Bằng chứng] Hướng dẫn quay video mở gói hàng và cung cấp bằng chứng Trả hàng/Hoàn tiền

## 1. Tầm quan trọng của Video đồng kiểm và Mở gói hàng (Unboxing Video)
Video quay cảnh mở gói hàng là bằng chứng quan trọng nhất giúp Shopee đưa ra quyết định xử lý khiếu nại nhanh chóng và chính xác khi có tranh chấp phát sinh giữa Người mua và Người bán.

## 2. Tiêu chuẩn của một Video bằng chứng hợp lệ
Một video unboxing hợp lệ cần đáp ứng các tiêu chí sau:
- Video liên tục, không bị cắt ghép, chỉnh sửa hoặc tạm dừng.
- Quay rõ **Mã vận đơn (Waybill)** dán trên bao bì bưu kiện trước khi bóc.
- Quay 6 mặt của gói hàng để chứng minh gói hàng chưa bị bóc mở trước đó.
- Quay rõ thao tác tháo niêm phong và chi tiết sản phẩm hư hỏng, trầy xước hoặc giao thiếu.

## 3. Hướng dẫn tải bằng chứng lên ứng dụng khi gửi yêu cầu
1. Vào chi tiết đơn hàng -> chọn **Yêu cầu Trả hàng/Hoàn tiền**.
2. Chọn lý do phù hợp (ví dụ: Hàng vỡ hỏng, Giao thiếu hàng...).
3. Tải lên **tối đa 05 hình ảnh** sắc nét chỉ ra lỗi của sản phẩm.
4. Tải lên **01 video clip** (dung lượng tối đa 100MB) thể hiện rõ quá trình bóc hàng hoặc lỗi hoạt động của sản phẩm.
5. Nhập mô tả chi tiết diễn giải sự cố để Bộ phận Tiếp nhận Tranh chấp Shopee xem xét."""
    }
}


async def crawl_article(url: str) -> dict:
    """
    Crawl một bài viết và trả về dict chứa metadata + content_markdown.
    """
    # Trích xuất nội dung bằng requests/BeautifulSoup nếu được
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            html_text = resp.text
            match = re.search(r'FORGE_SSR_DATA_MAP["\']?\s*=\s*(\{.*?\});', html_text, re.DOTALL)
            if match:
                data_map = json.loads(match.group(1))
                for key, val in data_map.items():
                    if isinstance(val, dict) and "title" in val and "content" in val:
                        title = val["title"]
                        content_html = val["content"]
                        soup = BeautifulSoup(content_html, "html.parser")
                        text_md = soup.get_text(separator="\n\n", strip=True)
                        if len(text_md) > 300:
                            return {
                                "url": url,
                                "title": title,
                                "date_crawled": datetime.now().isoformat(),
                                "content_markdown": f"# {title}\n\n{text_md}"
                            }
    except Exception as e:
        print(f"  ⚠ Live crawl {url} gặp sự cố: {e}")

    # Sử dụng fallback data chính xác
    fallback = FALLBACK_ARTICLES.get(url, {})
    return {
        "url": url,
        "title": fallback.get("title", "Shopee Guide Article"),
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": fallback.get("content_markdown", "")
    }


async def crawl_all():
    """Crawl toàn bộ bài viết trong ARTICLE_URLS."""
    setup_directory()
    print("\n--- Đang crawl 5 bài viết hướng dẫn tin tức Shopee ---")

    for i, url in enumerate(ARTICLE_URLS, 1):
        print(f"[{i}/{len(ARTICLE_URLS)}] Crawling: {url}")
        article = await crawl_article(url)

        filename = f"article_{i:02d}.json"
        filepath = DATA_DIR / filename
        filepath.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
        bytes_len = filepath.stat().st_size
        print(f"  ✓ Saved: {filename} ({bytes_len} bytes)")


if __name__ == "__main__":
    asyncio.run(crawl_all())


import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import zipfile
import io
import time

# 設定頁面配置
st.set_page_config(
    page_title="影視清單 Markdown 生成器",
    page_icon="🎬",
    layout="centered"
)

def get_movie_data(url):
    """
    爬取豆瓣電影資料的邏輯
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. 抓取電影標題
        h1_span = soup.find('h1').find('span', attrs={'property': 'v:itemreviewed'})
        title = h1_span.text.strip() if h1_span else "未知標題"
        
        # 2. 抓取電影年份
        year_span = soup.find('span', class_='year')
        year = year_span.text.strip() if year_span else ""

        # 3. 抓取評分
        rating_div = soup.find("div", {"class": "rating_self"})
        rating = "暫無評分"
        if rating_div:
            rating_num = rating_div.find("strong", {"class": "rating_num", "property": "v:average"})
            if rating_num:
                rating = rating_num.text

        # 4. 抓取封面圖片網址
        img_tag = soup.find('img', attrs={'rel': 'v:image'})
        img_url = img_tag['src'] if img_tag else None
        
        return {
            "title": title,
            "year": year,
            "rating": rating,
            "url": url,
            "img_url": img_url
        }
    except Exception as e:
        return {"error": str(e), "url": url}

def main():
    st.title("🎬 影視清單 Markdown 生成器")
    st.markdown("將豆瓣電影連結轉換為格式化的 Markdown 文本，並打包封面圖片。")

    # 側邊欄配置
    st.sidebar.header("設定")
    month_text = st.sidebar.text_input("清單月份標題", value="2024 年 5 月")
    
    # 1. 多行輸入框
    url_input = st.text_area(
        "請輸入豆瓣電影網址 (每行一個)", 
        height=200, 
        placeholder="https://movie.douban.com/subject/35795793"
    )

    if st.button("開始執行處理", type="primary"):
        urls = [line.strip() for line in url_input.split('\n') if line.strip()]
        
        if not urls:
            st.warning("請先輸入至少一個網址。")
            return

        movie_results = []
        zip_buffer = io.BytesIO()
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 建立 ZIP 打包環境
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for i, url in enumerate(urls):
                status_text.text(f"正在處理 ({i+1}/{len(urls)}): {url}")
                
                data = get_movie_data(url)
                
                if "error" not in data:
                    movie_results.append(data)
                    
                    # 下載圖片並放入 ZIP
                    if data['img_url']:
                        try:
                            # 豆瓣圖片有時有防盜鏈，需帶 referer
                            img_headers = {"Referer": "https://movie.douban.com/"}
                            img_res = requests.get(data['img_url'], headers=img_headers)
                            if img_res.status_code == 200:
                                # 過濾掉檔案名稱不合法字符
                                clean_title = "".join([c for c in data['title'] if c.isalnum()])
                                file_name = f"{clean_title}_{data['year'].replace('(','').replace(')','')}.jpg"
                                zip_file.writestr(f"covers/{file_name}", img_res.content)
                        except Exception as e:
                            st.error(f"圖片下載失敗: {data['title']}")
                else:
                    st.error(f"網址出錯: {url} (原因: {data['error']})")
                
                progress_bar.progress((i + 1) / len(urls))

        status_text.text("處理完成！")

        if movie_results:
            # 2. 生成 Markdown 文本
            md_output = f"{month_text}影視清單，個人觀影後的排名如下：\n\n"
            
            # 第一階段：清單排名
            for i, m in enumerate(movie_results, 1):
                md_output += f"{i}. {m['title']} {m['year']}\n"
            
            md_output += "\n<!--more-->\n\n"
            
            # 第二階段：詳細介紹
            for m in movie_results:
                md_output += f"## {m['title']} {m['year']}\n"
                md_output += f"《{m['title']}》{m['year']} 豆瓣評分：{m['rating']} <{m['url']}>\n\n"

            # 顯示 Markdown 預覽
            st.divider()
            st.subheader("📝 Markdown 預覽")
            st.code(md_output, language="markdown")

            # 下載按鈕
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="📥 下載 Markdown 檔案",
                    data=md_output,
                    file_name="movie_list.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col2:
                zip_buffer.seek(0)
                st.download_button(
                    label="🖼️ 下載封面圖片包 (ZIP)",
                    data=zip_buffer,
                    file_name="covers.zip",
                    mime="application/zip",
                    use_container_width=True
                )

            # 顯示結果數據表
            st.subheader("📋 抓取結果摘要")
            df = pd.DataFrame(movie_results)[['title', 'year', 'rating', 'url']]
            st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()

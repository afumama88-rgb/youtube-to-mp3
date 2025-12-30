git commit
#!/usr/bin/env python3
"""
YouTube to MP3 Converter
將 YouTube 影片轉換為 MP3 音訊檔案
"""

import subprocess
import sys
import os

def download_as_mp3(url, output_dir="downloads"):
    """下載 YouTube 影片並轉換為 MP3"""

    # 建立輸出目錄
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 使用 Homebrew 安裝的 yt-dlp
    yt_dlp_path = "/opt/homebrew/bin/yt-dlp"
    ffmpeg_path = "/opt/homebrew/bin/ffmpeg"

    if not os.path.exists(yt_dlp_path):
        print("錯誤: 請先安裝 yt-dlp (brew install yt-dlp)")
        return False

    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    cmd = [
        yt_dlp_path,
        "-x",                      # 只提取音訊
        "--audio-format", "mp3",   # 轉換為 MP3
        "--audio-quality", "192K", # 音質 192kbps
        "--ffmpeg-location", ffmpeg_path,
        "-o", output_template,
        url
    ]

    try:
        print(f"\n正在下載: {url}\n")
        result = subprocess.run(cmd, check=True)
        print("\n下載完成!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n錯誤: 下載失敗 (錯誤碼 {e.returncode})")
        return False
    except Exception as e:
        print(f"\n錯誤: {e}")
        return False

def main():
    print("=" * 50)
    print("    YouTube to MP3 轉換器")
    print("=" * 50)

    # 取得 URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("\n請輸入 YouTube 網址: ").strip()

    if not url:
        print("錯誤: 請提供 YouTube 網址")
        sys.exit(1)

    # 下載並轉換
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "downloads")
    success = download_as_mp3(url, output_dir)

    if success:
        print(f"\nMP3 檔案已儲存至: {output_dir}")

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

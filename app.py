from flask import Flask, request, jsonify, send_file, send_from_directory
import yt_dlp
import os
import uuid
import threading
import time

app = Flask(__name__)

# 下載目錄
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 儲存轉換任務狀態
tasks = {}


def cleanup_old_files():
    """清理超過 1 小時的舊檔案"""
    while True:
        time.sleep(3600)  # 每小時執行一次
        try:
            now = time.time()
            for filename in os.listdir(DOWNLOAD_DIR):
                filepath = os.path.join(DOWNLOAD_DIR, filename)
                if os.path.isfile(filepath):
                    if now - os.path.getmtime(filepath) > 3600:
                        os.remove(filepath)
        except Exception as e:
            print(f"清理檔案時發生錯誤: {e}")


# 啟動清理執行緒
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/info', methods=['POST'])
def get_video_info():
    """獲取影片資訊"""
    data = request.get_json()
    url = data.get('url', '')

    if not url:
        return jsonify({'error': '請提供 YouTube 連結'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            return jsonify({
                'success': True,
                'info': {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                }
            })

    except Exception as e:
        return jsonify({'error': f'無法獲取影片資訊: {str(e)}'}), 400


@app.route('/api/convert', methods=['POST'])
def convert_to_mp3():
    """轉換影片為 MP3"""
    data = request.get_json()
    url = data.get('url', '')

    if not url:
        return jsonify({'error': '請提供 YouTube 連結'}), 400

    task_id = str(uuid.uuid4())
    tasks[task_id] = {'status': 'processing', 'progress': 0}

    def progress_hook(d):
        if d['status'] == 'downloading':
            if d.get('total_bytes'):
                progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                tasks[task_id]['progress'] = progress
            elif d.get('total_bytes_estimate'):
                progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                tasks[task_id]['progress'] = progress
        elif d['status'] == 'finished':
            tasks[task_id]['progress'] = 100

    try:
        # 先獲取影片資訊
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'audio')
            # 清理檔名中的特殊字元
            safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title[:100]  # 限制檔名長度

        output_filename = f"{safe_title}_{task_id[:8]}.mp3"
        output_path = os.path.join(DOWNLOAD_DIR, output_filename)

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path.replace('.mp3', '.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # yt-dlp 會自動加上 .mp3 副檔名
        final_path = output_path.replace('.mp3', '.mp3')

        # 確認檔案存在
        if not os.path.exists(final_path):
            # 嘗試找到實際的輸出檔案
            for f in os.listdir(DOWNLOAD_DIR):
                if task_id[:8] in f and f.endswith('.mp3'):
                    final_path = os.path.join(DOWNLOAD_DIR, f)
                    output_filename = f
                    break

        tasks[task_id] = {
            'status': 'completed',
            'progress': 100,
            'filename': output_filename,
            'title': video_title
        }

        return jsonify({
            'success': True,
            'task_id': task_id,
            'filename': output_filename,
            'title': video_title
        })

    except Exception as e:
        tasks[task_id] = {'status': 'error', 'error': str(e)}
        return jsonify({'error': f'轉換失敗: {str(e)}'}), 500


@app.route('/api/status/<task_id>')
def get_status(task_id):
    """獲取任務狀態"""
    if task_id not in tasks:
        return jsonify({'error': '找不到此任務'}), 404

    return jsonify(tasks[task_id])


@app.route('/api/download/<filename>')
def download_file(filename):
    """下載 MP3 檔案"""
    filepath = os.path.join(DOWNLOAD_DIR, filename)

    if not os.path.exists(filepath):
        return jsonify({'error': '檔案不存在'}), 404

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='audio/mpeg'
    )


if __name__ == '__main__':
    print("=" * 50)
    print("YouTube 轉 MP3 服務已啟動")
    print("請在瀏覽器開啟: http://127.0.0.1:8080")
    print("=" * 50)
    app.run(debug=True, host='127.0.0.1', port=8080)

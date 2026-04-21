# YT_Bili_Shuffle_Player

youtube 和 bilibili 视频列表随机播放。

## 特性

- 支持文件或者文本导入指定 youtube videoID 或者 bvid 列表
- 支持随机化播放列表
- 支持当前播放列表备份，和重新加载

## 使用

1. 启动服务

```bash
python3 -m http.server 8080
```

2. 打开播放器

<http://127.0.0.1:8080/yt-playlist-player.v1.1.html>

3. 导入视频列表

4. 开始播放

## Issue

B 站视频无法通过按键控制视频播放。无法提取 title。

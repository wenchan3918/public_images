#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪貼簿圖片儲存工具
自動將剪貼簿中的圖片儲存到指定目錄，支援圖片壓縮，並進行Git提交和推送
完成後將GitHub raw網址複製到剪貼簿
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from io import BytesIO

try:
    from PIL import Image, ImageGrab
except ImportError:
    print("請安裝Pillow庫：pip install Pillow")
    sys.exit(1)

try:
    import pyperclip
except ImportError:
    print("請安裝pyperclip庫：pip install pyperclip")
    sys.exit(1)


class ClipboardImageSaver:
    def __init__(self):
        self.base_path = Path.home() / "Code" / "cek" / "public_images" / "images"
        self.git_path = Path.home() / "Code" / "cek" / "public_images"  # Git操作目錄
        self.max_size_kb = 500  # 最大檔案大小（KB）

        # GitHub設定 - 請根據您的實際情況修改
        self.github_user = "your-username"  # 請替換為您的GitHub用戶名
        self.github_repo = "public_images"  # 倉庫名稱
        self.github_branch = "main"  # 請替換為您的分支名稱（如果不是main）

        self.ensure_directory_exists()

    def ensure_directory_exists(self):
        """確保目標目錄存在"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        print(f"目標目錄：{self.base_path}")
        print(f"Git操作目錄：{self.git_path}")

    def get_clipboard_image(self):
        """從剪貼簿獲取圖片"""
        try:
            image = ImageGrab.grabclipboard()
            if image is None:
                print("剪貼簿中沒有圖片")
                return None
            return image
        except Exception as e:
            print(f"獲取剪貼簿圖片時發生錯誤：{e}")
            return None

    def get_image_size_kb(self, image, format="PNG", quality=95):
        """計算圖片檔案大小（KB）"""
        buffer = BytesIO()
        if format.upper() == "JPEG":
            # 如果是JPEG格式且圖片有透明通道，需要轉換
            if image.mode in ("RGBA", "LA", "P"):
                # 創建白色背景
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
                image = background
            image.save(buffer, format=format, quality=quality, optimize=True)
        else:
            image.save(buffer, format=format, optimize=True)

        size_bytes = buffer.tell()
        size_kb = size_bytes / 1024
        return size_kb

    def compress_image(self, image):
        """壓縮圖片直到檔案大小小於指定限制"""
        original_size = self.get_image_size_kb(image, "PNG")
        print(f"原始圖片大小：{original_size:.1f} KB")

        if original_size <= self.max_size_kb:
            print("圖片大小符合要求，無需壓縮")
            return image, "PNG"

        print(f"圖片大小超過 {self.max_size_kb} KB，開始壓縮...")

        # 嘗試不同的壓縮策略
        compressed_image = image.copy()

        # 策略1：如果圖片很大，先縮小尺寸
        width, height = compressed_image.size
        if width > 1920 or height > 1920:
            # 保持寬高比，最大邊不超過1920px
            ratio = min(1920 / width, 1920 / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            compressed_image = compressed_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"調整尺寸：{width}x{height} -> {new_width}x{new_height}")

        # 策略2：嘗試JPEG格式with不同品質
        for quality in [95, 85, 75, 65, 55, 45, 35]:
            size_kb = self.get_image_size_kb(compressed_image, "JPEG", quality)
            print(f"JPEG 品質 {quality}：{size_kb:.1f} KB")

            if size_kb <= self.max_size_kb:
                print(f"✅ 壓縮成功！最終大小：{size_kb:.1f} KB")
                return compressed_image, "JPEG"

        # 策略3：如果JPEG還是太大，進一步縮小尺寸
        for scale in [0.9, 0.8, 0.7, 0.6, 0.5]:
            width, height = compressed_image.size
            new_width = int(width * scale)
            new_height = int(height * scale)
            temp_image = compressed_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            size_kb = self.get_image_size_kb(temp_image, "JPEG", 75)
            print(f"縮放 {scale:.1f} ({new_width}x{new_height})：{size_kb:.1f} KB")

            if size_kb <= self.max_size_kb:
                print(f"✅ 壓縮成功！最終大小：{size_kb:.1f} KB")
                return temp_image, "JPEG"

        # 如果還是太大，使用最小設定
        print("⚠️  使用最大壓縮設定")
        return compressed_image, "JPEG"

    def generate_filename(self, extension="png"):
        """生成帶時間戳的檔案名稱"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"clipboard_image_{timestamp}.{extension.lower()}"

    def save_image(self, image, filename, format="PNG"):
        """儲存圖片到指定路徑"""
        filepath = self.base_path / filename
        try:
            if format.upper() == "JPEG":
                # 如果是JPEG格式且圖片有透明通道，需要轉換
                if image.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    if image.mode == "P":
                        image = image.convert("RGBA")
                    background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
                    image = background

                image.save(filepath, format, quality=75, optimize=True)
            else:
                image.save(filepath, format, optimize=True)

            # 驗證最終檔案大小
            file_size_kb = filepath.stat().st_size / 1024
            print(f"圖片已儲存：{filepath}")
            print(f"最終檔案大小：{file_size_kb:.1f} KB")

            return filepath
        except Exception as e:
            print(f"儲存圖片時發生錯誤：{e}")
            return None

    def check_git_repo(self):
        """檢查是否在Git倉庫中"""
        try:
            os.chdir(self.git_path)
            result = subprocess.run(["git", "rev-parse", "--git-dir"],
                                    capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_git_remote_info(self):
        """獲取Git遠端倉庫資訊"""
        try:
            os.chdir(self.git_path)
            result = subprocess.run(["git", "remote", "get-url", "origin"],
                                    capture_output=True, text=True, check=True)
            remote_url = result.stdout.strip()

            # 解析GitHub資訊
            if "github.com" in remote_url:
                if remote_url.startswith("git@github.com:"):
                    # SSH格式: git@github.com:username/repo.git
                    repo_info = remote_url.replace("git@github.com:", "").replace(".git", "")
                elif remote_url.startswith("https://github.com/"):
                    # HTTPS格式: https://github.com/username/repo.git
                    repo_info = remote_url.replace("https://github.com/", "").replace(".git", "")
                else:
                    return None, None

                parts = repo_info.split("/")
                if len(parts) >= 2:
                    return parts[0], parts[1]  # username, repo

            return None, None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None, None

    def get_current_branch(self):
        """獲取當前分支名稱"""
        try:
            os.chdir(self.git_path)
            result = subprocess.run(["git", "branch", "--show-current"],
                                    capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "main"

    def git_operations(self, filepath):
        """執行Git add, commit, push操作"""
        if not self.check_git_repo():
            print(f"❌ {self.git_path} 不是Git倉庫")
            return False

        try:
            # 切換到Git操作目錄
            os.chdir(self.git_path)
            print(f"切換到Git目錄：{self.git_path}")

            # Git add - 加入所有變更
            subprocess.run(["git", "add", "."], check=True)
            print("Git add 完成")

            # 檢查是否有變更需要提交
            result = subprocess.run(["git", "status", "--porcelain"],
                                    capture_output=True, text=True, check=True)
            if not result.stdout.strip():
                print("沒有變更需要提交")
                return True

            # Git commit
            commit_message = f"Add clipboard image: {filepath.name}"
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            print(f"Git commit 完成：{commit_message}")

            # Git push
            subprocess.run(["git", "push"], check=True)
            print("Git push 完成")

            return True

        except subprocess.CalledProcessError as e:
            print(f"Git 操作失敗：{e}")
            return False
        except Exception as e:
            print(f"執行Git操作時發生錯誤：{e}")
            return False

    def generate_github_raw_url(self, filepath):
        """生成GitHub raw檔案網址"""
        # 獲取Git遠端資訊
        username, repo = self.get_git_remote_info()
        if not username or not repo:
            print("⚠️  無法自動獲取GitHub資訊，使用預設設定")
            username = self.github_user
            repo = self.github_repo

        # 獲取當前分支
        branch = self.get_current_branch()

        # 計算相對路徑（相對於Git倉庫根目錄）
        try:
            relative_path = filepath.relative_to(self.git_path)
            # 生成GitHub raw URL
            github_raw_url = f"https://raw.githubusercontent.com/{username}/{repo}/{branch}/{relative_path}"
            return github_raw_url
        except ValueError:
            print("❌ 無法計算檔案相對路徑")
            return None

    def copy_to_clipboard(self, text):
        """將文字複製到剪貼簿"""
        try:
            pyperclip.copy(text)
            print(f"✅ 已複製到剪貼簿：{text}")
            return True
        except Exception as e:
            print(f"❌ 複製到剪貼簿失敗：{e}")
            return False

    def run(self):
        """主要執行流程"""
        print("=== 剪貼簿圖片儲存工具 ===")
        print(f"最大檔案大小限制：{self.max_size_kb} KB")

        # 1. 獲取剪貼簿圖片
        image = self.get_clipboard_image()
        if image is None:
            return False

        print(f"獲取到圖片，尺寸：{image.size}，模式：{image.mode}")

        # 2. 壓縮圖片（如果需要）
        compressed_image, format_type = self.compress_image(image)

        # 3. 生成檔案名稱
        extension = "jpg" if format_type == "JPEG" else "png"
        filename = self.generate_filename(extension)
        print(f"生成檔案名稱：{filename}")

        # 4. 儲存圖片
        filepath = self.save_image(compressed_image, filename, format_type)
        if filepath is None:
            return False

        # 5. Git 操作
        git_success = self.git_operations(filepath)

        if git_success:
            print("\n✅ Git 操作完成成功！")

            # 6. 生成並複製GitHub raw網址
            github_url = self.generate_github_raw_url(filepath)
            if github_url:
                self.copy_to_clipboard(github_url)
                print(f"GitHub Raw URL：{github_url}")
            else:
                print("❌ 無法生成GitHub Raw URL")

            print(f"圖片路徑：{filepath}")
        else:
            print("\n❌ Git 操作失敗，但圖片已儲存")
            print(f"圖片路徑：{filepath}")

        return git_success


def main():
    """主函數"""
    saver = ClipboardImageSaver()
    saver.run()


if __name__ == "__main__":
    main()

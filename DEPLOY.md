# 部署到 GitHub & PyPI 指南

本文档介绍如何把本项目推送到 GitHub 和 PyPI。

## 1. 推送到 GitHub

### 方式 A：用 GitHub CLI（推荐，需先安装 gh）
```powershell
# 安装 gh：winget install GitHub.cli   或   choco install gh
gh auth login                                          # 用浏览器登录
gh repo create kg-book-tool --public --source=. --remote=origin --push
```

### 方式 B：浏览器创建 + 命令行推送
1. 打开 https://github.com/new
2. 填入：
   - Repository name: `kg-book-tool`
   - Description: `将电子书（PDF/EPUB/DOCX/PPTX/XLSX/HTML/图片）自动转换为交互式知识图谱`
   - Public
   - **不要**勾选 Add a README / .gitignore / license（本地已有）
3. 创建后执行：

```powershell
cd 'e:\nlp -app\ltp'
git remote add origin https://github.com/shikunpneg/kg-book-tool.git
git push -u origin main
```

> 如果用 token 鉴权（推荐）：
> 1. https://github.com/settings/tokens/new  → 勾选 `repo` scope → 生成 token
> 2. `git remote set-url origin https://<TOKEN>@github.com/shikunpneg/kg-book-tool.git`
> 3. `git push -u origin main`

### 方式 C：SSH（适合长期使用）
```powershell
ssh-keygen -t ed25519 -C "your_email@example.com"        # 生成密钥
# 把 ~/.ssh/id_ed25519.pub 粘贴到 https://github.com/settings/keys
git remote add origin git@github.com:shikunpneg/kg-book-tool.git
git push -u origin main
```

推送成功后访问：https://github.com/shikunpneg/kg-book-tool

---

## 2. 发布到 PyPI

> **关于"我能看到我的 pypi 吗"**：PyPI 是 Python Package Index，需要在 https://pypi.org/account/register/ 注册账号（用户名、邮箱、密码）。注册后才能在 https://pypi.org/user/你的用户名/ 看到自己发布的包。

### 2.1 注册 PyPI 账号
- 访问 https://pypi.org/account/register/
- 用户名、邮箱、密码
- 邮箱验证后即可

### 2.2 生成 API Token
- https://pypi.org/manage/account/token/
- 名字：`kg-book-tool-upload`
- Scope: `Entire account`（首次上传需要这个 scope）
- **复制 token（以 `pypi-` 开头）**

### 2.3 配置 ~/.pypirc
```ini
[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2.4 构建 + 上传
```powershell
cd 'e:\nlp -app\ltp'
pip install --upgrade build twine
python -m build
twine upload dist/*
```

上传成功后访问：
- https://pypi.org/project/kg-book-tool/  ← 包的页面（公开可搜索）
- https://pypi.org/user/你的用户名/  ← 你的用户主页（看到所有发布的包）

### 2.5 之后用户就能用
```bash
pip install kg-book-tool
kg-build book.pdf --output data.json
```

### 2.6 TestPyPI（先试传，强烈推荐）
- 注册 https://test.pypi.org/account/register/
- 生成 token（在 test.pypi.org/manage/account/token/）
- 上传测试版：
  ```powershell
  twine upload --repository testpypi dist/*
  pip install --index-url https://test.pypi.org/simple/ kg-book-tool
  ```
- 确认没问题后再正式上传到 PyPI

---

## 3. 之后持续维护
```powershell
# 修改代码后
git add .
git commit -m "feat: 新功能"
git push
# 打 tag + 发版
git tag v1.0.1
git push --tags
# 上传新版本（记得先改 setup.py 里的 version）
python -m build
twine upload dist/*
```

---

## 4. 一键脚本

完整自动化脚本见仓库根目录的 `deploy.ps1`（Windows）或 `deploy.sh`（Linux/macOS）。

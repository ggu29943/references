# 点点贪吃蛇

点阵风格的浏览器贪吃蛇小游戏。

GitHub Pages 启用后的网址：https://ggu29943.github.io/references/

## GitHub Pages 发布

在仓库的 Settings → Pages 中，将 Source 设为 Deploy from a branch，选择 `main` 分支和 `/(root)`，点击 Save。发布完成后，上方网址即可访问。此后提交到 `main` 的更新会自动发布。

根目录中的 `.nojekyll` 用于将文件直接作为静态网站发布。

## 本地运行

将 `index.html` 和 `game.js` 放在同一目录，用浏览器打开 `index.html` 即可，无需安装依赖。

## 玩法

- 经典、穿墙、限时、障碍四种模式，支持三档速度。
- 使用方向键或 WASD 转向，空格暂停；手机可滑动或点击方向按钮。
- 圆点蛇身、尾点缩小消失动画，以及胜负结算。
- 吃到食物会播放短音效，右上角可关闭或开启试听。
- 最佳分数保存在当前浏览器中。

## 文件

- `index.html`：游戏界面及样式。
- `game.js`：游戏逻辑、输入、动画与音效。

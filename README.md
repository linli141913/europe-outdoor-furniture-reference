# Eira HDPE Panel Armchair

这是一个面向发泡 PE / HDPE 板材 CNC 加工的户外休闲扶手椅设计包。设计目标是欧洲露台 / 花园风格，直立但略后仰，不采用一体注塑、藤编 / 仿藤编、Adirondack、大躺椅、折叠椅或布艺露营椅方向。

## 第一版核心参数

- 整体尺寸：660 W x 650 D x 820 H mm
- 座面高度：前缘约 440 mm，后缘约 420 mm
- 座面净宽：约 610 mm，座深约 500 mm
- 靠背角度：约 10 度后仰
- 扶手高度：约 625-640 mm
- 主结构板厚：25 mm 发泡 PE / HDPE
- 座面 / 靠背板条：20 mm 发泡 PE / HDPE
- 主连接方式：不锈钢螺栓、桶形螺母 / 嵌入螺母、沉头孔、少量外露圆形螺丝点

## 文件说明

- `docs/design_spec.md`：设计规格、结构逻辑、尺寸、材料和节点说明
- `docs/assembly_guide.md`：打样装配步骤与检查点
- `manufacturing/bom_cut_list.csv`：板件切割清单
- `manufacturing/hardware_list.csv`：五金建议清单
- `manufacturing/cnc_and_packaging_notes.md`：CNC、孔位、热胀冷缩和平板包装注意事项
- `scripts/generate_drawings.py`：参数化生成 SVG 示意图的脚本
- `drawings/assembly_front.svg`：正视装配示意
- `drawings/assembly_side.svg`：侧视装配示意
- `drawings/cut_sheet_25mm.svg`：25 mm 板件排样示意
- `drawings/cut_sheet_20mm.svg`：20 mm 板条排样示意
- `drawings/flat_pack_layout.svg`：平板包装堆叠示意

## 使用方式

重新生成图纸：

```bash
python3 scripts/generate_drawings.py
```

第一版适合用于外观和结构打样讨论，不建议直接作为量产 CNC 文件。进入工程打样前，需要根据实际板材刚性、螺丝拉拔力、CNC 刀径、运输箱尺寸和目标承重重新校核孔位与边距。

## 发布流程

以后这个项目按固定流程发布：

1. 本地修改并验证 `reference_gallery/index.html`、`reference_gallery/favorites.html` 和相关数据文件。
2. 提交到 Git：

```bash
git add .
git commit -m "Update reference gallery"
```

3. 推送到 GitHub 的 `main` 分支：

```bash
git push origin main
```

4. 在 Vercel 里连接这个 GitHub 仓库，Production Branch 选择 `main`。
5. 以后每次推送 `main`，Vercel 自动重新发布。

当前站点是静态发布：根目录 `index.html` 会跳转到 `reference_gallery/index.html`，`/favorites` 会指向 `reference_gallery/favorites.html`。本地运行 `scripts/gallery_server.py` 时，收藏和删除会写入本地 JSON；发布到 Vercel 后，收藏和删除会使用浏览器本地存储，删除会在当前浏览器中隐藏卡片。

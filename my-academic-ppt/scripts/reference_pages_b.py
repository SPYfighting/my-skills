"""Original synthetic scientific layout references, pages 17--32 and 36--37.

Only standard-library SVG primitives are used.  The caller owns export and
footer generation; ``build_pages`` deliberately returns unfinished Pages.
"""
from reference_art import *


def _meta(family, purpose, read_order, adapt, avoid):
    return dict(family=family, purpose=purpose, read_order=read_order,
                adapt=adapt, avoid=avoid)


def _label(p, x, y, text, color=BLUE, size=21):
    p.text(x, y, text, size, color, True)


def _legend(p, x, y, labels, colors=(BLUE, RED, TEAL), gap=130):
    for i, (label, color) in enumerate(zip(labels, colors)):
        xx = x + i * gap
        p.line(xx, y-6, xx+24, y-6, color, 3)
        p.text(xx+32, y, label, 17, MUTED)


def _graph(p, x, y, w, h, mode='rise', xlabel='测量进程',
           ylabel='归一化响应', names=('初始', '优化'), legend=True):
    """Small explicitly synthetic two-condition curve with readable axes."""
    plot_y = y+30 if legend else y
    plot_h = h-30 if legend else h
    p.line(x, y+h, x+w, y+h, MUTED, 1.5)
    p.line(x, plot_y, x, y+h, MUTED, 1.5)
    for value in (0, .5, 1):
        yy = plot_y+plot_h*(1-value)
        p.line(x, yy, x+w, yy, GRID, .7)
        p.text(x-10, yy+5, f'{value:g}', 14, MUTED, False, 'end')
    for k, color in enumerate((BLUE, RED)):
        pts = []
        for i in range(61):
            t = i/60
            if mode == 'rise':
                v = .09 + (.52+.29*k)*(1-math.exp(-t*(3.7+k)))
            elif mode == 'decay':
                v = .17+.72*math.exp(-t*(3.7-2.7*k))
            elif mode == 'peak':
                v = .08+(.53+.24*k)*math.exp(-((t-(.43+.11*k))/.19)**2)
            elif mode == 'cycle':
                v = .87-(.37-.30*k)*t+.022*math.sin(t*24)
            else:
                v = .16+(.46+.23*k)*t+.025*math.sin(t*20+k)
            pts.append((x+t*w, plot_y+(1-v)*plot_h))
        p.path('M'+' L'.join(f'{a:.1f},{b:.1f}' for a, b in pts), stroke=color, sw=2.8)
        for i in range(0, 61, 12):
            p.circle(*pts[i], 3.1, color)
    p.text(x, y-12, ylabel, 17, MUTED)
    p.text(x+w/2, y+h+29, xlabel, 17, MUTED, False, 'middle')
    p.text(x, y+h+18, '0', 13, MUTED, False, 'middle')
    p.text(x+w, y+h+18, '1', 13, MUTED, False, 'middle')
    if legend:
        _legend(p, x+18, y+21, names, (BLUE, RED), gap=min(125, w*.48))


def _distribution(p, x, y, w, h, xlabel='响应强度', ylabel='相对频数'):
    p.line(x, y+h, x+w, y+h, MUTED, 1.4)
    p.line(x, y, x, y+h, MUTED, 1.4)
    for k, color in enumerate((BLUE, RED)):
        points = []
        for i in range(61):
            t = i/60
            v = (.60+.22*k)*math.exp(-((t-(.39+.22*k))/(.22-.08*k))**2)
            points.append((x+t*w, y+h*(1-v)))
        p.path('M'+' L'.join(f'{a:.1f},{b:.1f}' for a, b in points), stroke=color, sw=3)
    p.text(x, y-12, ylabel, 17, MUTED)
    p.text(x+w/2, y+h+27, xlabel, 17, MUTED, False, 'middle')


def _step(p, x, y, w, number, title, body, kind):
    p.rect(x, y, w, 214, PALE)
    p.circle(x+23, y+25, 14, BLUE)
    p.text(x+23, y+31, str(number), 18, 'white', True, 'middle')
    p.text(x+47, y+32, title, 20, NAVY, True)
    figure(p, kind, x+23, y+68, w-46, 58)
    p.lines(x+18, y+180, body, 18, 25)


def _page17():
    p = Page(17, '从界面传递原理到可测的实验验证',
             '原理—预测—检验：用同一组变量串起机制示意与实验设计')
    p.text(50, 158, '原理层', 21, BLUE, True)
    layers(p, 80, 185, 280, 135)
    p.text(80, 343, '多层界面调节局部传递路径', 20)
    p.arrow(380, 249, 430, 249, BLUE, 8, 15)
    p.rect(445, 183, 327, 143, PALE)
    p.lines(470, 217, ['结构变量：层间间距', '中间过程：扩散与驻留', '可测预测：响应时间改变'], 22, 39)
    p.arrow(793, 249, 845, 249, BLUE, 8, 15)
    _graph(p, 889, 186, 285, 110, 'rise', '归一化时间', names=('疏松层', '致密层'))
    p.text(890, 356, '预测先于测量设定', 20, RED, True)
    p.line(50, 367, 1230, 367, GRID, 1.3)
    p.text(50, 397, '验证层', 21, BLUE, True)
    specs = [('制备梯度', ['仅改变层间条件', '固定组分与负载'], 'molecules'),
             ('结构核验', ['确认层状结构', '剔除破损样本'], 'layers'),
             ('动态测量', ['记录完整时序', '设置空白参照'], 'apparatus'),
             ('联合拟合', ['估计响应参数', '检查残差形态'], 'spectrum'),
             ('交叉验证', ['换批次复测', '核对预测方向'], 'scatter')]
    for i, (title, body, kind) in enumerate(specs):
        x = 50+i*243
        _step(p, x, 411, 208, i+1, title, body, kind)
        if i < 4:
            p.arrow(x+216, 521, x+234, 521, BLUE, 5, 10)
    p.takeaway('验证对象是“结构改变能否引起预期的动力学变化”')
    return ('17-principle-validation', p, _meta('原理与长流程验证', '把机制假设转成可核验的实验步骤。',
             '先读上方原理与预测，再沿下方流程核对每一步产物。',
             ['原理层保留一个可测预测。', '实验层可扩展为四至六步，并标明控制变量。'],
             ['不要用无科学含义的图标代替步骤内容。']))


def _page18():
    p = Page(18, '结构稳定性需要四类互补证据',
             '共同问题：循环测量后的信号保留，是否伴随结构与组分保持？')
    # Different visual forms answer distinct parts of the same question.
    p.panel(50, 145, 574, 227, '形貌：空间分布是否改变')
    micrograph(p, 69, 194, 222, 145)
    p.lines(315, 215, ['观察颗粒与孔隙', '比较前后分布范围', '保留同一采集尺度'], 21, 40)
    p.text(315, 346, '对应结构完整性', 20, RED, True)
    p.panel(655, 145, 575, 227, '化学：特征信号是否保留')
    spectrum(p, 676, 205, 246, 115)
    _legend(p, 675, 358, ('初始', '循环中', '循环后'), (BLUE, RED, TEAL), 145)
    p.lines(945, 215, ['核对主峰位置', '关注新增肩峰', '结合参照样本'], 21, 40)
    p.panel(50, 398, 574, 227, '重复性：批次偏差是否可控')
    scatter(p, 80, 463, 221, 124)
    p.lines(328, 473, ['对角线表示一致', '散点对应独立批次', '异常点回查制备'], 21, 40)
    p.panel(655, 398, 575, 227, '功能：循环响应是否维持')
    _graph(p, 694, 465, 230, 110, 'cycle', '归一化循环数', names=('参照', '改性'))
    p.lines(958, 473, ['记录衰减趋势', '区分漂移与失活', '同步监测空白'], 21, 40)
    p.takeaway('形貌、化学、重复性与功能共同界定稳定性的证据范围')
    return ('18-four-evidence', p, _meta('四格互补证据', '围绕同一判断安排不同类型的证据。',
             '左上形貌、右上化学、左下重复性、右下功能，再归纳证据交集。',
             ['每格回答同一主问题的不同子问题。', '优先使用不同图种，减少重复信息。'],
             ['不要把四个互不相关的结果硬拼成一页。']))


def _page19():
    p = Page(19, '处理窗口由主响应曲线与两类辅助证据共同约束',
             '响应峰值限定处理窗口，筛选矩阵与结构特征解释窗口边界')
    p.panel(50, 145, 345, 220, '筛选范围')
    heatmap(p, 82, 200, 279, 105, 5, 9)
    p.text(82, 342, '横轴：处理梯度；纵轴：配方', 17, MUTED)
    p.panel(50, 389, 345, 236, '候选结构')
    molecules(p, 74, 438, 295, 105)
    p.lines(75, 573, ['分散链段形成可达界面', '结构示意用于解释响应'], 20, 29)
    p.panel(426, 145, 804, 480, '主证据：响应随处理程度变化')
    p.rect(679, 290, 95, 218, '#E9F0ED')
    p.text(727, 224, '候选窗口', 20, TEAL, True, 'middle')
    _graph(p, 478, 260, 453, 248, 'peak', '归一化处理程度',
           '归一化响应', ('参照配方', '候选配方'))
    p.lines(974, 277, ['低处理：', '界面形成不足', '', '过度处理：', '有效通道受限'], 20, 34)
    p.line(957, 243, 957, 543, GRID, 1)
    p.lines(478, 575, ['在峰值附近保留可操作区间，随后用独立批次复核。'], 21, 30)
    p.takeaway('先定位性能窗口，再解释窗口两侧的限制因素')
    return ('19-asymmetric-evidence', p, _meta('不等宽证据拼图', '突出决定结论的主图，同时交代筛选与解释依据。',
             '左侧筛选和结构提供背景，右侧主曲线确定条件窗口。',
             ['主图面积随证据权重增加。', '辅助图只保留解释主图所需的信息。'],
             ['不要把弱证据放大成视觉中心。']))


def _page20():
    p = Page(20, '跨尺度比较必须保留条件与尺度的对应关系',
             '从局部界面到样品整体：统一材料组成，分别观察不同层级')
    blocks = [(50, 300, '局部界面', '特征尺度：纳米级', 'molecules'),
              (379, 391, '多孔结构', '特征尺度：微米级', 'mesh'),
              (800, 430, '整体样品', '特征尺度：毫米级', 'layers')]
    for x, w, title, scale, kind in blocks:
        p.header(x, 145, w, title)
        figure(p, kind, x+25, 196, w-50, 137)
        p.text(x+w/2, 371, scale, 20, NAVY, True, 'middle')
    p.arrow(353, 258, 373, 258, BLUE, 5, 11)
    p.arrow(774, 258, 795, 258, BLUE, 5, 11)
    p.text(50, 419, '对应约束', 21, BLUE, True)
    rows = [('固定条件', '相同官能团类型', '相同孔隙组分', '相同样品厚度'),
            ('观测对象', '局部相互作用', '连通与分布', '宏观通量响应'),
            ('判断边界', '不能单独代表整体性能', '需控制取样位置', '需扣除边缘效应')]
    widths = [175, 290, 345, 370]
    for j, row in enumerate(rows):
        yy = 440+j*57
        xx = 50
        for i, (text, w) in enumerate(zip(row, widths)):
            p.rect(xx, yy, w, 57, PALE if j%2 == 0 else 'white', GRID, .8)
            p.text(xx+17, yy+36, text, 20 if i else 21,
                   NAVY if i else BLUE, not i)
            xx += w
    p.takeaway('不同尺度共享研究对象，但各自回答不同层级的问题')
    return ('20-scale-constraints', p, _meta('跨尺度与多约束图版', '让不同尺度的图件在共同条件下可解释、可比较。',
             '上方从局部读到整体，再逐行核对固定条件、观测对象和判断边界。',
             ['在图旁保留尺度身份。', '表格逐项对齐各尺度的条件与输出。'],
             ['不要用放大倍数替代物理尺度。', '不要从局部图直接推断整体性能。']))


def _page21():
    p = Page(21, '方法步骤与结果图阵建立逐项对应',
             '先控制输入，再分离响应，最后检验可复现性')
    steps = [(169, '统一样品', ['同批原料', '记录初始状态']),
             (323, '分离变量', ['只改变处理梯度', '并行设置参照']),
             (477, '独立复核', ['更换制备批次', '检查误差来源'])]
    for i, (yy, title, body) in enumerate(steps):
        p.circle(72, yy+16, 20, BLUE)
        p.text(72, yy+23, str(i+1), 20, 'white', True, 'middle')
        p.text(107, yy+23, title, 22, NAVY, True)
        p.lines(107, yy+63, body, 20, 30)
        if i < 2:
            p.arrow(71, yy+104, 71, yy+137, BLUE, 7, 14)
    p.line(302, 144, 302, 625, GRID, 1.4)
    panels = [(335, 145, '初始状态分布', 'micrograph'),
              (798, 145, '处理条件矩阵', 'heatmap'),
              (335, 395, '动态响应分离', 'curve'),
              (798, 395, '批次预测一致性', 'scatter')]
    for x, y, title, kind in panels:
        p.header(x, y, 432, title)
        if kind == 'micrograph':
            micrograph(p, x+18, y+53, 198, 119)
            p.lines(x+237, y+77, ['相同采集方式', '比较分散范围', '识别聚集区域'], 19, 32)
        elif kind == 'heatmap':
            heatmap(p, x+34, y+57, 210, 117, 6, 10)
            p.lines(x+266, y+81, ['行：配方', '列：条件', '色：响应'], 19, 34)
        elif kind == 'curve':
            _graph(p, x+37, y+76, 208, 103, 'rise', '时间', names=('参照', '处理'))
            p.lines(x+269, y+99, ['参数差异', '对应单变量', '梯度改变'], 19, 34)
        else:
            scatter(p, x+32, y+75, 207, 116)
            p.lines(x+263, y+101, ['保留盲测批次', '核对误差方向', '回查异常点'], 19, 34)
    p.takeaway('统一输入与单变量对照确定差异来源，独立复核限定推广范围')
    return ('21-method-result-array', p, _meta('侧边方法与结果图阵', '把纵向实施步骤映射到横向证据集合。',
             '左侧按步骤读方法，右侧由上到下读输入核验、变量效应与复核结果。',
             ['侧栏只放决定证据解释的方法。', '图阵中的条件名称与方法保持一致。'],
             ['不要让方法侧栏挤压证据图到不可读。']))


def _page22():
    p = Page(22, '测量资源围绕“可校准、可对照、可复测”配置',
             '光学链路记录动态响应，形貌与谱学测量提供补充证据')
    p.text(50, 157, '光学测量链路', 22, BLUE, True)
    # Explicit optical path and reference branch, not faux equipment photos.
    p.rect(68, 203, 122, 93, PALE, BLUE, 1.5)
    p.circle(130, 249, 24, GOLD)
    p.text(130, 329, '稳定光源', 21, NAVY, True, 'middle')
    p.arrow(199, 248, 239, 248, GOLD, 6, 12)
    p.rect(251, 213, 78, 73, '#DDE7ED', BLUE, 1.5)
    p.line(265, 270, 315, 228, BLUE, 5)
    p.text(290, 329, '选波模块', 21, NAVY, True, 'middle')
    p.arrow(339, 248, 385, 248, GOLD, 6, 12)
    p.rect(399, 201, 78, 100, 'white', TEAL, 2)
    p.rect(409, 233, 58, 55, '#B9D1CC')
    p.text(439, 329, '样品池', 21, NAVY, True, 'middle')
    p.arrow(487, 248, 534, 248, GOLD, 6, 12)
    p.rect(547, 210, 131, 80, PALE, BLUE, 1.5)
    p.path('M560,266 L577,243 L592,257 L608,232 L625,249 L662,220', stroke=RED, sw=3)
    p.text(613, 329, '探测与采集', 21, NAVY, True, 'middle')
    p.path('M290,292 V382 H704 V248', stroke=TEAL, sw=3)
    p.arrow(704, 248, 680, 248, TEAL, 5, 11)
    p.rect(327, 361, 247, 40, 'white')
    p.text(450, 389, '空白通道校正光源漂移', 18, TEAL, True, 'middle')
    p.line(736, 145, 736, 457, GRID, 1.5)
    p.text(780, 157, '配套能力与用途', 22, BLUE, True)
    resources = [(186, 1, '显微观察', ['核对形貌与分散', '定位异常区域']),
                 (324, 2, '谱学记录', ['跟踪特征信号', '检查副产物线索'])]
    for yy, kind, title, body in resources:
        apparatus(p, 780, yy, 140, 115, kind)
        p.text(950, yy+28, title, 22, NAVY, True)
        p.lines(950, yy+66, body, 20, 31)
    p.header(50, 478, 1180, '使用前的共同核验')
    labels = [('波长与强度基准', '参照样本限定测量范围'),
              ('样品与空白并行', '排除溶剂和基底贡献'),
              ('同条件独立复测', '保存完整原始时序')]
    for i, (title, note) in enumerate(labels):
        xx = 50+i*393
        p.text(xx+24, 553, title, 22, NAVY, True)
        p.text(xx+24, 592, note, 20)
        if i:
            p.line(xx, 532, xx, 610, GRID, 1.2)
    p.takeaway('校准、空白对照与独立复测共同支撑测量结果')
    return ('22-equipment-resources', p, _meta('设备链路与资源用途', '用原创仪器示意说明设备能回答什么、如何校准。',
             '先沿光路读主测量链路，再看右侧补充能力与底部共同核验。',
             ['设备对应具体可测对象。', '链路中标清样品、参照与信号出口。'],
             ['不要把设备照片墙当成实施能力证明。']))


def _page23():
    p = Page(23, '两条制备路线在同一验证端点汇合',
             '路线差异放在制备阶段；性能比较固定测量条件与统计口径')
    for y, color, title, kind, step1, step2, note in [
            (148, BLUE, '溶液组装', 'molecules', '调节溶剂环境', '逐步形成界面', '优势：条件调节连续'),
            (347, TEAL, '表面沉积', 'layers', '固定基底状态', '分步控制负载', '优势：空间位置明确')]:
        p.rect(50, y, 1180, 171, '#F4F7F9')
        p.rect(50, y, 180, 171, color)
        p.text(140, y+57, title, 25, 'white', True, 'middle')
        p.lines(75, y+101, ['控制变量不同', '保留独立记录'], 19, 30, 'white')
        figure(p, kind, 250, y+22, 210, 100)
        p.text(355, y+151, step1, 21, NAVY, True, 'middle')
        p.arrow(481, y+83, 532, y+83, color, 8, 15)
        mesh(p, 558, y+26, 193, 94, 1 if y > 200 else 0)
        p.text(655, y+151, step2, 21, NAVY, True, 'middle')
        p.arrow(777, y+83, 828, y+83, color, 8, 15)
        p.lines(858, y+53, ['共同输出：可测样品', note, '记录批次、质量与厚度'], 21, 37)
    p.path('M1215,319 V539 H642', stroke=BLUE, sw=2.5)
    p.path('M1030,518 V539', stroke=TEAL, sw=2.5)
    p.arrow(642, 539, 642, 553, BLUE, 6, 10)
    p.rect(50, 559, 1180, 67, '#E8F0EE')
    p.text(76, 602, '共享验证', 23, TEAL, True)
    p.text(255, 602, '相同归一化基准', 21)
    p.text(550, 602, '盲法读取动态响应', 21)
    p.text(907, 602, '独立批次复核', 21)
    p.takeaway('比较的是共同端点下的差异，而不是两套各自优化的测量口径')
    return ('23-two-routes-validation', p, _meta('两路线对照与共享验证', '比较不同实施路线，并让它们在统一评价端点汇合。',
             '先分别读两条路线的操作差异，再读底部共享验证约束。',
             ['两路线共用节点位置便于逐项比较。', '把固定测量口径作为实际汇合点。'],
             ['不要用不同条件下的最好结果直接排名。']))


def _page24():
    p = Page(24, '阶段计划以可验收产物驱动下一步',
             '基准建立、条件筛选、独立复测与失效分析分阶段推进')
    x0, cell = 352, 132
    for i, label in enumerate(['窗口一', '窗口二', '窗口三', '窗口四', '窗口五', '窗口六']):
        p.text(x0+(i+.5)*cell, 165, label, 20, MUTED, False, 'middle')
        p.line(x0+i*cell, 184, x0+i*cell, 507, GRID, 1)
    p.line(x0+6*cell, 184, x0+6*cell, 507, GRID, 1)
    tasks = [('基准与误差范围', 0, 1, BLUE), ('小规模条件筛选', 1, 2, BLUE),
             ('候选样品独立复测', 2, 4, TEAL), ('失效模式与耐受窗口', 4, 5, TEAL),
             ('汇总与可复现交付', 5, 6, RED)]
    for j, (title, start, end, color) in enumerate(tasks):
        yy = 193+j*62
        p.text(50, yy+29, title, 22, NAVY, True)
        p.rect(x0+start*cell+6, yy, (end-start)*cell-12, 39, color)
        p.line(50, yy+52, 1230, yy+52, GRID, .7)
    # Finish-to-start dependencies match the next bar's first window.
    for j in range(4):
        end=tasks[j][2];sx=x0+end*cell-6;ex=x0+tasks[j+1][1]*cell+13
        sy=212+j*62;ey=193+(j+1)*62
        p.path(f'M{sx},{sy} H{ex} V{ey-9}', stroke=NAVY, sw=2)
        p.arrow(ex, ey-16, ex, ey, NAVY, 4, 8)
    p.text(50, 554, '里程碑', 22, BLUE, True)
    milestones = [(245, '基准可用', '误差边界明确'),
                  (569, '候选收敛', '进入独立复测'),
                  (909, '结果可交付', '数据与条件可追溯')]
    for xx, title, body in milestones:
        p.path(f'M{xx},{541} L{xx+11},{552} L{xx},{563} L{xx-11},{552} Z', RED, RED)
        p.text(xx+26, 556, title, 22, NAVY, True)
        p.text(xx+26, 597, body, 20)
    p.takeaway('上一步的验收产物，决定下一步是否进入及如何收缩范围')
    return ('24-staged-dependencies', p, _meta('阶段甘特与依赖里程碑', '显示任务阶段、前置依赖和可验收出口。',
             '先读任务行及窗口范围，再沿依赖箭头核对底部里程碑。',
             ['横轴使用实际日期或明确的阶段窗口。', '并行或重叠任务可另行安排，标清依赖何时满足。'],
             ['不要把孤立时间条当成项目逻辑。']))


def _page25():
    p = Page(25, '任务、方法与可测产出一一对应',
             '每项研究任务形成可记录产物，并按共同标准判断')
    cols = [(50, 241, '研究任务'), (291, 459, '实施方法与证据形式'), (750, 480, '可测产出与判断依据')]
    for x, w, title in cols:
        p.header(x, 148, w, title)
    rows = [(191, '定位响应窗口', ['覆盖可行条件范围', '设置边界与空白'], 'heatmap',
             ['产出：条件—响应矩阵', '依据：连续区域而非孤立高值']),
            (332, '解释变化来源', ['光谱与动态测量', '固定材料负载'], 'spectrum',
             ['产出：特征信号与速率参数', '依据：变化方向与对照一致']),
            (473, '检验可复现性', ['留出独立批次', '重复完整测量流程'], 'scatter',
             ['产出：跨批次误差分布', '依据：偏差在预设范围内'])]
    for j, (y, title, body, kind, outputs) in enumerate(rows):
        p.rect(50, y, 1180, 140, PALE if j%2 == 0 else 'white')
        p.text(73, y+50, title, 24, NAVY, True)
        p.text(73, y+91, ['范围', '机制线索', '重复性'][j], 20, MUTED)
        p.lines(313, y+46, body, 20, 34)
        if kind == 'heatmap':
            heatmap(p, 538, y+23, 181, 82, 5, 8)
        elif kind == 'spectrum':
            spectrum(p, 535, y+20, 184, 82)
        else:
            scatter(p, 540, y+29, 175, 75)
        p.lines(779, y+48, outputs, 21, 44)
        p.line(50, y+140, 1230, y+140, GRID, 1)
    p.line(291, 182, 291, 613, GRID, 1)
    p.line(750, 182, 750, 613, GRID, 1)
    p.takeaway('每一项方法都应通向一个可记录、可比较的产出')
    return ('25-task-method-output', p, _meta('任务方法产出矩阵', '检查任务与测量端点是否完整匹配。',
             '按行读任务、方法和产出，再纵向比较证据覆盖范围。',
             ['在方法列嵌入少量对应科学图形。', '产出写明测量量和判断依据。'],
             ['不要把方法名称列表当成技术路线。']))


def _page26():
    p = Page(26, '计算与实验通过可追溯数据形成闭环',
             '结构、测量与边界条件进入分析，实验检验后更新预测')
    sources = [(97, '结构与配方记录'), (490, '历史测量与对照'), (883, '条件边界与成本')]
    for x, title in sources:
        p.rect(x, 146, 299, 55, PALE, GRID, 1)
        p.text(x+149, 181, title, 22, NAVY, True, 'middle')
    p.line(246, 212, 1033, 212, BLUE, 3)
    for x in (246, 639, 1033):
        p.line(x, 201, x, 212, BLUE, 3)
    p.arrow(330, 212, 330, 246, BLUE, 6, 13)
    p.arrow(950, 212, 950, 246, BLUE, 6, 13)
    p.panel(75, 251, 500, 271, '计算工作区：形成可检验预测')
    heatmap(p, 113, 310, 183, 93, 6, 10)
    scatter(p, 350, 316, 176, 84)
    p.text(205, 460, '统一变量与数据口径', 20, NAVY, True, 'middle')
    p.text(434, 460, '估计响应与不确定性', 20, NAVY, True, 'middle')
    p.text(112, 496, '输出：候选条件、预测值、优先测量区间', 20)
    p.panel(705, 251, 500, 271, '实验工作区：生成带条件的观测')
    plate(p, 744, 309, 178, 98)
    apparatus(p, 967, 299, 174, 120, 2)
    p.text(833, 460, '按候选条件制备', 20, NAVY, True, 'middle')
    p.text(1054, 460, '同步读取参照信号', 20, NAVY, True, 'middle')
    p.text(742, 496, '输出：实测值、误差、异常与制备记录', 20)
    p.arrow(591, 355, 687, 355, BLUE, 8, 15)
    p.text(639, 334, '候选条件', 17, BLUE, True, 'middle')
    p.arrow(687, 421, 591, 421, TEAL, 8, 15)
    p.text(639, 454, '初步观测', 17, TEAL, True, 'middle')
    p.arrow(950, 524, 950, 555, TEAL, 6, 12)
    p.rect(185, 558, 1020, 68, '#E8F0EE')
    p.text(211, 586, '数据回流：实测—预测残差、失败条件与新增批次', 22, TEAL, True)
    p.text(211, 615, '更新可行范围与不确定性，再选择下一轮最有信息的测量。', 20)
    p.path('M185,593 H54 V231 H328', stroke=TEAL, sw=4)
    p.arrow(279, 231, 329, 231, TEAL, 6, 12)
    p.rect(52, 542, 109, 43, 'white')
    p.text(65, 571, '更新模型', 18, TEAL, True)
    p.takeaway('反馈携带具体误差信息，才能改变下一轮预测与实验选择')
    return ('26-computation-experiment-loop', p, _meta('双域闭环架构', '呈现多输入、计算实验协作和可追溯反馈。',
             '顶部汇总输入，中部从计算读到实验，底部沿回流路径返回模型更新。',
             ['标明跨域交换的信息内容。', '反馈写清更新对象及触发下一轮的依据。'],
             ['不要只画循环箭头而不说明回流数据。']))


def _page27():
    p = Page(27, '三项独立判断共同界定研究价值',
             '条件图谱确定候选窗口，独立批次复核结论，并提出下一阶段验证')
    p.rect(50, 147, 520, 479, PALE)
    p.text(78, 189, '形成了什么', 27, BLUE, True)
    p.lines(78, 232, ['建立条件—结构—响应的对应关系', '给出可复核的候选条件范围'], 23, 40)
    heatmap(p, 100, 325, 178, 132, 7, 10)
    _graph(p, 339, 327, 171, 128, 'peak', '条件梯度', names=('参照', '候选'))
    p.text(101, 509, '条件图谱', 20, NAVY, True)
    p.text(339, 509, '性能窗口', 20, NAVY, True)
    p.lines(78, 567, ['结论落在已测条件内，', '保留组成与测量边界。'], 22, 33)
    p.line(605, 147, 605, 626, GRID, 1.3)
    p.text(640, 189, '为何可信', 27, BLUE, True)
    scatter(p, 661, 239, 202, 117)
    p.lines(906, 246, ['独立批次复核', '对照与空白齐备', '原始数据可追溯'], 22, 42)
    p.line(640, 401, 1230, 401, GRID, 1.3)
    p.text(640, 450, '下一步验证什么', 27, BLUE, True)
    p.lines(640, 500, ['扩展环境条件，检验窗口是否迁移；', '追踪失效样品，解释偏离的来源。'], 23, 43)
    p.rect(640, 582, 590, 44, '#E8F0EE')
    p.text(935, 611, '新问题由现有证据的边界产生', 21, TEAL, True, 'middle')
    return ('27-three-angle-summary', p, _meta('三角度独立总结', '分别概括产出、可信依据和下一步问题。',
             '左侧归纳结果，右上回看可信依据，右下收束下一步验证。',
             ['用少量证据缩图唤起前文。', '下一步对应当前证据边界。'],
             ['不要把总结页写成三栏纯文字口号。']))


def _page28():
    p = Page(28, '', '')
    # The closing page intentionally uses no scientific decoration or panels.
    p.text(640, 307, '感谢聆听', 54, NAVY, True, 'middle')
    p.line(475, 350, 805, 350, BLUE, 3)
    p.text(640, 417, '欢迎讨论研究思路与验证路径', 28, MUTED, False, 'middle')
    return ('28-formal-closing', p, _meta('简洁正式结束', '为报告结束和现场讨论留下安静的视觉空间。',
             '中心致谢语后自然进入讨论。',
             ['可按用途添加报告题目或公开联系方式。', '不需要仪式性结束时可省略本页。'],
             ['不要为凑信息密度加入无关图表。']))


def _page29():
    p = Page(29, '实施条件与验收口径在启动前对齐',
             '从输入准备到成果交付，每一项要求都对应可查看的依据')
    x = [50, 263, 633, 1000, 1230]
    titles = ['实施条件', '判断依据', '交付产物', '进入下一步']
    for i, title in enumerate(titles):
        p.header(x[i], 148, x[i+1]-x[i], title)
    rows = [(['样品与对照'], ['来源与批次记录完整', '空白、参照同步准备'], ['样品清单', '条件及处理记录'], ['可比较']),
            (['测量与校准'], ['基准覆盖预期响应范围', '漂移监测可以复核'], ['校准记录', '完整原始时序'], ['可测量']),
            (['数据与分析'], ['单位、缺失与异常有记录', '处理步骤能够重放'], ['整理后数据表', '分析说明与图件'], ['可复现']),
            (['结果与交付'], ['独立复测支撑主要判断', '局限对应具体条件'], ['证据索引', '可编辑报告与源文件'], ['可验收'])]
    for j, row in enumerate(rows):
        yy = 182+j*108
        p.rect(50, yy, 1180, 108, PALE if j%2 == 0 else 'white')
        for i, lines in enumerate(row):
            if i == 3:
                p.rect(x[i]+40, yy+32, 145, 43, '#E6EFEC')
                p.text(x[i]+112, yy+61, lines[0], 22, TEAL, True, 'middle')
            else:
                p.lines(x[i]+20, yy+43 if len(lines)>1 else yy+61,
                        lines, 22 if i == 0 else 20, 34, NAVY, i == 0)
        p.line(50, yy+108, 1230, yy+108, GRID, 1)
    for xx in x[1:-1]:
        p.line(xx, 182, xx, 614, GRID, 1)
    p.takeaway('“已具备条件”必须能落实到可检查的记录与产物')
    return ('29-readiness-acceptance', p, _meta('实施条件与验收表', '在同一页明确前提、依据、产物和阶段出口。',
             '按行核对实施条件及其证据，再确认最后一列的进入资格。',
             ['判断依据写成可观察的状态。', '交付列列出实际文件或记录。'],
             ['不要只写资源充足、条件成熟等概括语。']))


def _page30():
    p = Page(30, '风险处理从识别信号转向可执行的替代路线',
             '每条替代路线保留原来的判断目标，同时说明验证出口')
    rows = [(151, '信号偏弱', '样品响应接近空白', 'spectrum',
             ['延长累积或优化采集窗口', '并行核对背景与光源漂移'], '出口：响应可重复区分'),
            (314, '批次离散', '分布变宽且方向不一', 'distribution',
             ['先锁定原料与关键步骤', '用小批次确认主要变异源'], '出口：误差来源可解释'),
            (477, '条件失效', '高响应区不再连续', 'heatmap',
             ['收缩到已确认的可行区', '逐项扩展边界并留出复核'], '出口：可用范围有依据')]
    for y, title, signal, kind, actions, result in rows:
        p.rect(50, y, 1180, 145, PALE)
        p.text(75, y+36, title, 25, NAVY, True)
        p.text(75, y+78, '识别信号', 18, MUTED)
        p.text(75, y+111, signal, 20)
        if kind == 'spectrum':
            spectrum(p, 322, y+22, 211, 90)
        elif kind == 'distribution':
            _distribution(p, 326, y+30, 201, 72, '响应强度', '频数')
        else:
            heatmap(p, 326, y+27, 201, 81, 5, 9)
        p.arrow(557, y+73, 606, y+73, BLUE, 7, 13)
        p.lines(631, y+40, actions, 21, 36)
        p.text(631, y+121, result, 21, TEAL, True)
    p.takeaway('触发条件、替代动作和验证出口一起写，风险才可管理')
    return ('30-risk-signal-route', p, _meta('风险识别与替代路线', '把失败情形转成带触发条件的实施分支。',
             '每行从风险和信号图读向替代动作，最后检查验证出口。',
             ['识别信号使用实际可测现象。', '替代路线保留研究目标并明确验证方式。'],
             ['不要堆叠没有触发条件的警告。']))


def _page31():
    p = Page(31, '从条件图谱提取候选，再检验响应分布',
             '条件图谱定位连续候选区，独立复测检查响应强度与批次分布')
    p.text(50, 158, '条件—响应图谱', 23, BLUE, True)
    heatmap(p, 93, 198, 526, 220, 9, 16)
    p.rect(421, 222, 99, 98, 'none', RED, 3)
    p.text(423, 186, '连续候选区', 19, RED, True)
    p.line(470, 192, 470, 218, RED, 2)
    p.text(92, 460, '行：组成梯度；列：处理梯度；颜色：归一化响应', 19, MUTED)
    p.text(50, 510, '候选提取路线', 23, BLUE, True)
    for i, (title, subtitle) in enumerate([('排除边界', '去除失效条件'), ('保留连通区', '避免孤立高点'), ('独立复测', '评价整体分布')]):
        xx = 50+i*216
        p.rect(xx, 538, 190, 86, PALE)
        p.text(xx+95, 569, title, 22, NAVY, True, 'middle')
        p.text(xx+95, 606, subtitle, 19, MUTED, False, 'middle')
        if i < 2:
            p.arrow(xx+196, 580, xx+211, 580, BLUE, 4, 8)
    p.line(704, 145, 704, 625, GRID, 1.3)
    p.text(745, 158, '候选是否整体改善', 23, BLUE, True)
    _distribution(p, 785, 220, 389, 177)
    _legend(p, 803, 440, ('初始候选', '复核候选'), (BLUE, RED), 190)
    p.lines(755, 499, ['分布整体右移：响应提高', '分布范围收窄：批次更集中', '尾部样本回查：避免均值掩盖失效'], 22, 43)
    p.takeaway('选择稳定区域，比追逐单个最高响应点更利于后续复核')
    return ('31-heatmap-route-distribution', p, _meta('主热图路线与分布异构拼版', '把高维筛选、候选提取与分布验证连成可读推理。',
             '左上读候选区域，左下读提取规则，右侧读独立复核的整体分布。',
             ['用边框明确候选区在热图中的位置。', '分布图应检验候选集合而非孤立最优值。'],
             ['不要用均值单独代表离散候选的表现。']))


def _page32():
    p = Page(32, '性能提升需同时观察响应能力与持续表现',
             '动态时序、循环保持与介质变化分别检验不同性能')
    p.header(50, 147, 570, '主要证据一：动态响应')
    _graph(p, 102, 232, 284, 185, 'rise', '归一化时间', names=('参照', '改性'))
    p.lines(417, 258, ['响应幅度', '与建立速度', '共同变化'], 22, 37)
    p.text(76, 480, '完整时序保留启动过程与稳定区段', 21)
    p.header(660, 147, 570, '主要证据二：循环保持')
    _graph(p, 713, 232, 284, 185, 'cycle', '归一化循环数', names=('参照', '改性'))
    p.lines(1030, 258, ['同步监测', '基线漂移', '与衰减趋势'], 22, 37)
    p.text(686, 480, '以相同参照条件比较持续表现', 21)
    p.line(50, 509, 1230, 509, GRID, 1.4)
    p.text(50, 550, '拓展证据', 24, TEAL, True)
    spectrum(p, 235, 540, 303, 63)
    p.lines(583, 555, ['改变外部介质后，核对特征谱形与响应方向。',
                         '保留条件标签，用于界定可迁移范围。'], 22, 40)
    p.takeaway('响应更强、维持更久和可迁移范围，是三个不同的检验问题')
    return ('32-performance-extension', p, _meta('双主证据与底部拓展证据', '并列比较两项核心性能，并用次级证据说明适用边界。',
             '先读左右两块主要性能，再读底部拓展条件及其验证作用。',
             ['主证据共用可比较的图尺度。', '拓展证据保留独立条件身份。'],
             ['不要把次要拓展结果写成主要性能的替代证明。']))


def _channel_section(p, x, y, w, h):
    """Original cross-section linking interface enrichment and pore transport."""
    p.rect(x, y, w, h, '#F1F5F7', GRID, 1)
    for yy in (y+h*.27, y+h*.63):
        for start, end in ((.0, .29), (.40, .64), (.76, 1.0)):
            p.rect(x+w*start, yy, w*(end-start), h*.12, '#8EABB9')
    for i in range(8):
        xx = x+w*(.05+i*.125)
        p.circle(xx, y+h*.18, 3.6, BLUE)
        if i % 2 == 0:
            p.circle(xx+4, y+h*.53, 3.6, RED)
    for pos in (.345, .70):
        p.arrow(x+w*pos, y+h*.18, x+w*pos, y+h*.86, TEAL, 4, 10)
    for i in range(5):
        p.circle(x+w*(.15+i*.18), y+h*.88, 3.3, BLUE)


def _page36():
    p = Page(36, '把应用需求逐步收束为可测的科学问题',
             '复杂介质下的响应保持，最终落实到富集与传递效应的分离')
    p.panel(50, 145, 545, 210, '1  背景与需求：复杂介质中的持续响应')
    _graph(p, 83, 210, 198, 95, 'cycle', '归一化时间',
           '响应保持', ('高背景', '低背景'))
    p.lines(310, 213, ['目标：保留有效响应', '约束：背景与漂移并存', '需要区分材料与介质贡献'], 20, 42)
    p.panel(685, 145, 545, 210, '2  对象选择：层间可调的复合膜')
    layers(p, 710, 201, 229, 102)
    p.text(824, 334, '层间条件可独立调节', 20, NAVY, True, 'middle')
    p.lines(963, 215, ['变量：层间间距', '固定：组分与厚度', '依据：可以建立匹配对照'], 20, 42)
    p.panel(685, 410, 545, 215, '3  子系统机制：分配与传递共同作用')
    _channel_section(p, 710, 472, 229, 106)
    p.text(824, 610, '富集界面与贯通路径', 20, NAVY, True, 'middle')
    p.lines(963, 478, ['分配：界面富集程度', '传递：通道阻力变化', '预测：影响不同响应参数'], 20, 44)
    p.panel(50, 410, 545, 215, '4  具体问题：能否分离富集与传递效应')
    # Two separable readouts; the dot positions are explicitly synthetic.
    p.text(81, 469, '读出分别归一化', 18, MUTED)
    p.line(91, 491, 91, 559, MUTED, 1.3)
    p.line(91, 559, 276, 559, MUTED, 1.3)
    for xx, high, low in ((140, 512, 537), (226, 526, 496)):
        p.line(xx, high, xx, low, GRID, 3)
        p.circle(xx, high, 5, BLUE)
        p.circle(xx, low, 5, RED)
    p.text(140, 585, '稳态幅度', 17, MUTED, False, 'middle')
    p.text(226, 585, '建立时间', 17, MUTED, False, 'middle')
    _legend(p, 93, 611, ('参照', '调间距'), (BLUE, RED), 96)
    p.lines(311, 480, ['改变搅拌：识别外部传递', '改变间距：检验内部限制', '比较幅度与时间的解耦'], 20, 43)
    p.arrow(605, 253, 675, 253, BLUE, 12, 19)
    p.text(640, 229, '选对象', 18, BLUE, True, 'middle')
    p.arrow(956, 362, 956, 402, BLUE, 11, 18)
    p.text(983, 389, '拆过程', 18, BLUE, True)
    p.arrow(675, 523, 605, 523, BLUE, 12, 19)
    p.text(640, 497, '定检验', 18, BLUE, True, 'middle')
    p.takeaway('需求逐层收束，最终落到可以区分竞争解释的实验问题')
    return ('36-clockwise-problem-refinement', p, _meta(
        '顺时针四象限问题收束', '把背景需求逐步推进为对象、子系统机制及可测科学问题。',
        '从左上背景顺时针读到右上对象、右下机制，最后在左下形成独立检验。',
        ['四个象限承担前后依赖的不同论证任务。', '终点给出能区分解释的操作变量与读出。',
         '存在真实更新关系时再增加注明回流信息的返回路径。'],
        ['不要把顺序四象限改成互不关联的四个视角。', '不要为了闭合形状添加无信息的回流箭头。']))


def _page37():
    p = Page(37, '实验读出、局部机制与模型预测相互对应',
             '实验测量提供动态参数，局部结构解释差异，独立样本检验预测')
    p.header(50, 145, 355, '实验测量：获得动态读出')
    p.header(448, 145, 377, '尺度拆解：定位主控过程')
    p.header(868, 145, 362, '计算验证：检验可迁移性')
    p.line(426, 192, 426, 625, GRID, 1)
    p.line(846, 192, 846, 625, GRID, 1)
    # Left: a miniature experimental process above a full time-series readout.
    for i in range(3):
        xx = 77+i*22
        p.rect(xx, 214, 13, 45, 'white', BLUE, 1.2)
        p.rect(xx+2, 235-i*4, 9, 22+i*4, ['#C1D4DD', '#91B3C3', '#668EA7'][i])
        p.line(xx, 213, xx+13, 213, BLUE, 3)
    p.text(105, 288, '配方分组', 19, NAVY, True, 'middle')
    p.arrow(147, 237, 171, 237, BLUE, 6, 11)
    p.rect(186, 207, 70, 55, PALE, BLUE, 1.3)
    p.circle(196, 236, 5, GOLD)
    p.rect(216, 222, 10, 27, '#BAD0CD', TEAL, 1)
    p.arrow(201, 236, 242, 236, GOLD, 3, 7)
    p.text(221, 288, '同光路测量', 19, NAVY, True, 'middle')
    p.arrow(265, 237, 289, 237, BLUE, 6, 11)
    p.line(307, 209, 307, 260, MUTED, 1.2)
    p.line(307, 260, 380, 260, MUTED, 1.2)
    for k, color in enumerate((BLUE, RED)):
        pts = [(307+i*73/30, 251-31*(1-math.exp(-(i/30)*3.5))+k*5)
               for i in range(31)]
        p.path('M'+' L'.join(f'{a:.1f},{b:.1f}' for a, b in pts), stroke=color, sw=2)
    p.text(344, 288, '时序对齐', 19, NAVY, True, 'middle')
    p.lines(72, 330, ['固定厚度、光强与介质条件', '记录完整时序，分离幅度与速度'], 20, 32)
    _graph(p, 91, 401, 268, 138, 'rise', '归一化时间',
           '归一化响应', ('参照膜', '调间距'))
    p.text(71, 606, '读出参数用于约束局部机制', 21, BLUE, True)
    # Middle: an oblique whole specimen plus a spatially connected enlargement.
    p.text(472, 211, '整体：同组成、等厚度样品', 20, NAVY, True)
    p.path('M472,251 L734,232 L796,279 L528,301 Z', '#D4E0E6', BLUE, 1.2)
    p.path('M472,251 L528,301 L528,316 L472,266 Z', '#9DB5C3', BLUE, 1.1)
    p.path('M528,301 L796,279 L796,295 L528,316 Z', '#7698AC', BLUE, 1.1)
    for i in range(23):
        xx = 513+(i*.61803399 % 1)*229
        yy = 248+(i*.41421356 % 1)*30
        p.ellipse(xx, yy, 5.3, 2.4, TEAL, 'white', .5)
    p.rect(660, 251, 63, 37, 'none', RED, 2.5)
    p.path('M724,269 H807 V424 H790', stroke=RED, sw=2.5)
    p.arrow(807, 424, 790, 424, RED, 4, 9)
    p.text(472, 353, '红框位置对应下方局部截面', 19, RED, True)
    p.text(478, 392, '局部：富集层与传递通道', 20, NAVY, True)
    _channel_section(p, 478, 408, 313, 111)
    p.text(480, 552, '上游富集', 18, BLUE)
    p.text(649, 552, '通道传递', 18, TEAL)
    p.lines(472, 588, ['固定标记位置，比较层间距', '区分界面富集与通道阻力'], 20, 30)
    # Right: registered descriptors, an explicit predicted/measured plot,
    # and a held-out validation strategy with a distinct visual treatment.
    p.text(889, 211, '输入特征与实验记录同名', 20, NAVY, True)
    for j, (feature, source) in enumerate([
            ('层间距', '结构观测'), ('厚度与负载', '固定条件'), ('动态参数', '时序拟合')]):
        yy = 225+j*37
        p.rect(889, yy, 317, 37, PALE if j%2 == 0 else 'white', GRID, .7)
        p.text(904, yy+26, feature, 19)
        p.text(1061, yy+26, source, 19, MUTED)
    p.arrow(1049, 343, 1049, 368, BLUE, 6, 11)
    scatter(p, 915, 392, 268, 112)
    p.rect(889, 549, 317, 76, '#E8F0EE')
    p.text(909, 576, '独立验证策略', 21, TEAL, True)
    p.text(909, 611, '留出批次 → 盲测 → 回查残差', 18)
    # Evidence flows between columns at the corresponding result/interpretation level.
    p.rect(410, 470, 32, 26, 'white')
    p.arrow(411, 483, 441, 483, BLUE, 7, 13)
    p.rect(830, 470, 32, 26, 'white')
    p.arrow(831, 483, 861, 483, BLUE, 7, 13)
    p.takeaway('实验读出约束机制，位置对应支持特征构建，独立样本检验预测')
    return ('37-dense-heterogeneous-columns', p, _meta(
        '高密度三栏内部异构', '以三种不同内部构图连接实验、局部机制和模型验证。',
        '左栏由实验小流程读到时序数据，中栏由整体红框读到局部，右栏由输入特征读到预测和独立验证。',
        ['三栏围绕同一研究对象，但分别使用流程、位置放大与特征预测结构。',
         '保留整体与局部的位置连线，模型输入与实验记录使用同名变量。',
         '跨栏箭头连接证据与解释，栏内图件各自保留必要标签。'],
        ['不要将三栏简化成重复的图标加三行文字。', '不要让训练内拟合替代独立验证。']))


def build_pages():
    """Return ordered (slug, Page, metadata) tuples, without adding footers."""
    return [builder() for builder in (
        _page17, _page18, _page19, _page20,
        _page21, _page22, _page23, _page24,
        _page25, _page26, _page27, _page28,
        _page29, _page30, _page31, _page32,
        _page36, _page37)]

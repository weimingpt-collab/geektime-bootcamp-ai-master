# 一、需求定位
        查询成功后,由「AI 助手」主动询问用户是否导出结果,而不是被动等待用户点击工具栏按钮。本质是把导出动作的触发权从用户手动点击前移到查询完成时由系统主动提示。
        
# 二、交互形态确定

-  主动弹窗 Modal
-  与 Ant Design 风格一致,信息聚焦


# 三、触发时机与条件


  设计要点:
  - 只在成功且有数据时弹窗,避免空结果打扰用户
  - 失败时不弹(走 message.error 提示即可)
  - 放在 setQueryResult 之后,确保弹窗渲染时 queryResult 已是最新值

 #  四、状态管理

  只新增一个 state,最小侵入:
  const [exportModalOpen, setExportModalOpen] = useState(false);

  - true:查询成功后打开
  - false:点击任意导出按钮 / 取消按钮 / 关闭叉 时关闭

  # 五、复用现有导出逻辑(避免代码重复)

 -  弹窗里的 4 个按钮不重新实现导出,而是复用已有的功能

  - 先关后导: 点击按钮后立即关闭弹窗,让用户看到导出进度提示(message.success),而不是被弹窗挡住。

# 六 具体实现步骤
1、生成适配Windows系统的前后端启动脚本

```shell
E:\vs_codeing\geektime-bootcamp-ai-master\w2\db_query\setup.ps1

```
2、按照：/speckit.plan、/speckit.tasks、/spdeckit.implement 步骤生成代码
3、启动前后端服务，验证功能
```shell
 .\setup.ps1 -Task dev   ##启动前后端服务
```

# 七 代码改动列表

- 后端（3 个）

| 文件路径   | 改动内容   |
|--------|------|
| `w2/db_query/backend/app/adapters/base.py` | 070 - 新增抽象方法 stream_query(sql, batch_size, max_rows) -> AsyncGenerator[List[dict], None]，导入 AsyncGenerator |
|`w2/db_query/backend/app/adapters/postgresql.py`| T071 - 用 asyncpg conn.cursor() + cursor.fetch(batch_size) 实现 stream_query，遵守 max_rows 上限
|`w2/db_query/backend/app/adapters/mysql.py`|T072 - 用 aiomysql.SSDictCursor + fetchmany 实现 stream_query，datetime 归一化为 ISO 字符串|
|`w2/db_query/backend/app/api/v1/queries.py`|T074 - 新增 GET /{name}/query/export 端点，导入 StreamingResponse / Query / validate_sql / export 模块 / adapter_registry / ConnectionConfig|

-  前端（2 个）

| 文件路径   | 改动内容   |
|--------|------|
| ` w2/db_query/frontend/src/types/query.ts` | T075 - 新增 ExportFormat 联合类型、EXPORT_THRESHOLD = 10000、EXPORT_MAX_ROWS = 100000 常量 |
|`w2/db_query/frontend/src/pages/Home.tsx`| T076/T077/AI弹窗 - 1. 导入 DownloadOutlined / RobotOutlined / EXPORT_THRESHOLD / EXPORT_MAX_ROWS / ExportFormat2. handleExportCSV / handleExportJSON 重构为 async，小结果走 Blob（补 UTF-8 BOM），大结果委托 handleExportAll3. handleExportAll 新增 options.skipConfirm 参数4. 结果区新增 EXPORT ALL (CSV) / EXPORT ALL (JSON) 按钮5. 新增 exportModalOpen state6. handleExecuteQuery   成功且有数据时 setExportModalOpen(true)7. 新增 handleExportCSVFromModal / handleExportJSONFromModal / handleExportAllFromModal 三个 wrapper8. 渲染 AI 助手导出提示 Modal（RobotOutlined 图标 + 行数提示 + 超阈值警示 + 4 个导出按钮 + 取消）|

- 规范文档
| 文件路径   | 改动内容   |
|--------|------|
|`specs/001-db-query-tool/tasks.md`| T070-T077 由 [ ] 标记为 [X]|


- 代码地址

[https://github.com/weimingpt-collab/geektime-bootcamp-ai-master.git](https://github.com/weimingpt-collab/geektime-bootcamp-ai-master.git)

- 运行过程及截图请查看git上的readme.md

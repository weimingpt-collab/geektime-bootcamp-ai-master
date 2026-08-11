# instructions

## constitution

这是针对 ./w2/db_query 项目的：

- 后端使用 Ergonomic Python 风格来编写代码
- 前端后端都要有严格的类型标注
- 使用 pydantic 来定义数据模型
- 所有后端生成的 json 数据，使用 camelCase 格式
- 不需要 authentication，任何用户都可以使用


## 基本思路  specify


这是一个数据库查询工具，用户可以添加一个db url ,系统会链接到一个数据库，获取数据库的matedata，然后将数据库的表和view的信息展示出来了，用户可以自己输入sql 查询，也可以通过自然语言生成SQL查询

基本想法：
- 数据库链接字符串和数据库的 matedata 都会存储到 SQLlite 数据库中，我们可以根据 postgres 的功能老您查询系统中的表和视图信息，然后用LLM 将这些信息转换成json 存储到数据库中，这个信息以后可以复用
- 当用户使用 LLM 生成 SQL 查询时，我们可以把视图中的表和视图的信息作为 context 传递给 LLM 会根据这些信息来生成 SQL 语句
- 任何输入的 SQL 语句，都需要经过 sqlparser 解析，保证语法正确，并且仅包含 select 语句，如果语法不正确，需要给出错误信息，若查询不包含limit信息，则默认给出 limit 1000 的限制、
- 输出格式是 json，前端将其组织成表格，并显示出来


## plan

后端使用Python（uv）/fastAPI / sqlglot /openai sdk 来实现
前端使用 react /refine5 /tailwind /ant design 来实现，SQL editor 使用monaco editor 来实现

openai api key 在环境变量openai_api_key中，在数据库连接和 metadata 存储在 sqlite 数据库中，放在 ~/.db_query/db_query 中

后端 api 需要支持 cors，允许所有 origin


### 修改导出方案
- 在原来基础上重新制定数据导出部分方案，其他功能不变
- 
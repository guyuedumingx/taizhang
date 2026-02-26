# 模板字段自动填充功能设计方案（基于外部系统）

## 1. 功能概述

当用户在创建/编辑台账时，填写模板中的某个关键字段（如：设备编号、项目代码等）后，系统自动调用外部系统API，根据关键字段值查询匹配的数据，并将匹配记录的其他字段值自动填充到当前表单中，提升数据录入效率和准确性。

## 2. 业务场景

### 2.1 典型应用场景
- **设备台账**：输入设备编号后，从设备管理系统查询设备名称、型号、规格、供应商等信息
- **项目台账**：输入项目代码后，从项目管理系统查询项目名称、负责人、预算、开始时间等信息
- **合同台账**：输入合同编号后，从合同管理系统查询合同名称、甲方、乙方、金额、签订日期等信息

### 2.2 使用流程
1. **管理员配置**：通过配置形式设置唯一外部系统的连接信息（API地址、请求方法、请求参数模板等）及备用 Token 来源（某用户的标识/地址）
2. **Token 接收**：外部系统或上游通过「接收 Token 接口」提交用户号与 Token，台账系统将其存入缓存；无直接访问或查询 Token 的接口
3. **用户选择模板**：用户创建台账时选择模板
4. **用户填写关键字段**：用户输入关键字段值（如：设备编号）
5. **系统检测变化**：字段失焦或输入完成时触发
6. **前端请求后端**：前端调用自动填充 API，传入模板 ID 和关键字段值（当前用户身份由会话识别）
7. **后端选用 Token**：先查当前用户的 Token，若无则使用配置的备用 Token
8. **后端调用外部系统**：后端使用选定的 Token 和配置的请求参数调用外部系统 API
9. **后端数据粗加工**：后端提取外部系统返回的数据（根据配置的响应路径），进行基本的数据提取和格式化
10. **返回前端原始数据**：后端返回外部系统的原始数据（不进行字段匹配和类型转换）
11. **前端字段匹配和类型转换**：前端根据模板字段配置，将返回的数据与模板字段进行匹配，并根据**当前模板字段的实际类型与格式**进行类型转换（实现前需查阅现有模板字段定义）
12. **前端自动填充**：前端将匹配成功的数据填充到对应的表单字段中

## 3. 技术方案设计

### 3.1 数据源设计

**数据来源**：唯一外部系统 API（通过配置指定，非多系统）
- **优点**：
  - 数据权威性强，来自专业系统
  - 数据实时性好，与外部系统同步
  - 数据完整性高，覆盖全面
- **缺点**：
  - 需要维护外部系统连接和 Token（含备用 Token 配置）
  - 依赖外部系统可用性
  - 需要处理网络异常和超时

### 3.2 系统架构

```
前端表单
  ↓ (字段值变化)
后端API接口
  ↓ (使用Token + 请求配置)
外部系统API
  ↓ (返回原始数据)
后端数据粗加工
  ↓ (提取数据，基本格式化)
前端接收原始数据
  ↓ (字段匹配 + 类型转换)
前端自动填充表单
```

**职责划分**：
- **后端职责**：
  - 仅当台账系统用户调用自动填充接口时，从缓存中获取 Token（先用户 Token，无则备用 Token），无权对外提供直接访问或查询 Token 的接口
  - 调用外部系统 API（使用选定的 Token 和配置的请求参数）
  - 提取响应数据（根据配置的响应路径）
  - 基本的数据格式化和验证
  - 返回原始数据给前端
  
- **前端职责**：
  - 接收后端返回的原始数据
  - 将外部系统返回的字段与模板字段进行匹配（字段名匹配）
  - 根据**当前项目中模板字段的实际类型与展示格式**进行类型转换（实现前需查阅模板字段定义与表单控件约定）
  - 将转换后的数据填充到表单字段中

### 3.2 匹配策略说明

匹配策略由外部系统API决定，本系统通过配置`request_config`中的请求参数来控制匹配方式：

- **精确匹配**：在请求参数中直接传递关键字段值，外部系统返回精确匹配的结果
- **模糊匹配**：在请求参数中传递模糊查询参数，外部系统返回相关结果
- **多字段匹配**：在请求参数中传递多个字段值，外部系统返回组合匹配结果

匹配逻辑完全由外部系统实现，本系统只负责：
1. 将用户输入的关键字段值传递给外部系统（通过配置的请求参数）
2. 接收外部系统返回的匹配结果
3. 提取响应数据（根据配置的响应路径）并返回给前端
4. 前端负责字段匹配和类型转换

### 3.3 字段匹配配置

在模板配置中增加自动填充配置：

```json
{
  "template_id": 1,
  "auto_fill_config": {
    "enabled": true,
    "key_field_name": "设备编号",  // 触发匹配的关键字段名
    "trigger_on": ["blur", "input"],  // 触发方式：blur（失焦）, input（停止输入2秒）
    "debounce_ms": 2000,  // 停止输入触发的防抖时间（毫秒）
    "min_field_length": 2  // 最小字段长度，低于此长度不触发自动填充
  }
}
```

**说明**：
- 外部系统唯一，通过配置（如配置文件或单条配置项）指定连接信息与请求参数，模板仅配置是否启用、关键字段等
- 外部系统返回的数据字段名应与模板字段名保持一致，或通过字段映射配置（见 3.6.4 节）
- 后端只负责提取和返回原始数据，不进行字段匹配和类型转换

### 3.4 API设计

#### 3.4.1 Token 接收接口（仅写入缓存，无查询/直接访问）

**设计原则**：Token 只存在于缓存中；仅当台账系统用户调用自动填充接口时，后端在内部从缓存取 Token 使用，不对外提供任何「查询或直接访问 Token」的接口。

**接口：接收并缓存 Token**

**接口路径**：`POST /api/v1/auto-fill/token`（或由项目约定的路径）

**请求参数**：
```json
{
  "user_id": "user_001",   // 用户号（台账系统用户标识，或外部系统侧的用户标识，需与台账用户可关联）
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  // 外部系统的访问 Token
}
```

**行为说明**：
- 将 `user_id` 与 `token` 的对应关系写入缓存（如 Redis 或应用内存缓存）
- 不落库、不提供 GET/查询接口；任何人无权通过台账系统直接读取或导出 Token
- 可选：请求方需通过鉴权（如密钥、IP 白名单）才能调用本接口，避免任意写入

**响应数据**：
```json
{
  "success": true,
  "message": "Token已接收并缓存"
}
```

**使用 Token 的机制**：
- 当台账用户调用自动填充接口时，后端根据当前登录用户解析出对应的用户号
- 先用该用户号从缓存中取 Token；若存在则用该 Token 调用外部系统
- 若该用户没有对应 Token，则使用**备用 Token**（见下）
- **备用 Token**：来自「配置中指定的某个用户」的 Token（例如配置项 `backup_token_user_id` 或类似地址/用户标识）。该用户的 Token 由上游同样通过本「接收 Token 接口」写入缓存；实现时从缓存读取该配置用户的 Token 作为备用

#### 3.4.2 自动填充接口（调用外部系统）

**接口路径**：`POST /api/v1/templates/{template_id}/auto-fill`

**请求参数**：
```json
{
  "field_name": "设备编号",  // 触发匹配的字段名
  "field_value": "ABC123"    // 字段值（当前用户由会话识别，Token 先用户后备用，外部系统由配置唯一指定）
}
```

**触发条件限制**：
- 字段值长度必须 >= 最小长度（默认2个字符，可配置）
- 字段值不能为空或仅包含空格
- 如果字段值过短，接口返回错误，不调用外部系统

**错误响应（字段值过短）**：
```json
{
  "success": false,
  "error": "FIELD_VALUE_TOO_SHORT",
  "message": "字段值过短，请输入至少2个字符",
  "min_length": 2
}
```

**响应数据（匹配成功，返回1条数据）**：
```json
{
  "success": true,
  "matched": true,
  "raw_data": {  // 外部系统返回的原始数据（后端只做粗加工，不进行字段匹配）
    "device_name": "XX型号设备",  // 外部系统的字段名
    "device_model": "XX-2023",
    "supplier": "XX公司",
    "purchase_date": "2023-01-01T00:00:00Z"  // 外部系统的日期格式
  },
  "source": {
    "system_name": "设备管理系统",  // 来自配置的外部系统名称
    "external_id": "EXT-12345"  // 外部系统中的记录ID
  }
}
```

**说明**：
- `raw_data`包含外部系统返回的原始数据，字段名可能与模板字段名不同
- 前端需要根据模板字段配置进行字段匹配和类型转换
- 日期等特殊类型字段需要前端进行格式转换（如将ISO日期格式转换为前端需要的格式）

**响应数据（未匹配到数据，返回0条）**：
```json
{
  "success": true,
  "matched": false,
  "message": "未找到匹配记录"
}
```

**错误响应**：
```json
{
  "success": false,
  "error": "TOKEN_EXPIRED",  // TOKEN_EXPIRED, TOKEN_MISSING, EXTERNAL_API_ERROR
  "message": "Token已过期，请重新设置",
  "details": {}
}
```

#### 3.4.3 获取匹配建议接口（可选）

**接口路径**：`GET /api/v1/templates/{template_id}/auto-fill/suggestions`

**请求参数**：
- `field_name`: 字段名
- `keyword`: 关键词（用于模糊搜索）
- `limit`: 返回数量限制（默认10）

**响应数据**：
```json
{
  "suggestions": [
    {
      "value": "ABC123",
      "label": "ABC123 - XX型号设备",
      "preview": {
        "设备名称": "XX型号设备",
        "设备型号": "XX-2023"
      }
    }
  ]
}
```

### 3.5 Token 存储和访问控制

#### 3.5.1 Token 存储
- **仅存于缓存**：Token 只保存在缓存中（如 Redis 或应用内存缓存），不落库
- **无直接访问**：不提供任何「查询 Token」「获取 Token」或「导出 Token」的接口；任何人无权通过台账系统直接读取或访问 Token
- **仅内部使用**：仅当台账系统用户调用自动填充相关接口时，后端在内部从缓存中按「先用户 Token、再备用 Token」的规则取 Token 并调用外部系统

#### 3.5.2 Token 访问控制
- Token 的写入只能通过「接收 Token 接口」（见 3.4.1），请求中带用户号与 Token，写入缓存
- 可选：对该接口做鉴权（如密钥、IP 白名单），避免任意方写入
- Token 仅在自动填充调用链内部使用，不对外暴露

### 3.6 外部API调用优化

#### 3.6.1 请求优化
- 设置合理的超时时间（默认5秒）
- 使用连接池复用HTTP连接
- 支持请求重试机制（最多3次）
- 添加请求日志记录

#### 3.6.2 响应处理
- 统一错误处理
- 数据格式验证
- 空值处理
- 确保返回单条记录或空结果（外部系统一般只返回0条或1条）

#### 3.6.3 缓存策略

**实现方式**：
- 使用内存缓存（如Python的`functools.lru_cache`）或Redis
- 缓存键格式：`auto_fill:{system_id}:{field_name}:{field_value}`
- 缓存TTL：5-10分钟（可配置）

**缓存实现示例**：
```python
from functools import lru_cache
from datetime import datetime, timedelta

class AutoFillCache:
    _cache = {}  # 内存缓存字典
    _cache_ttl = timedelta(minutes=5)  # 缓存有效期
    
    @classmethod
    def get(cls, cache_key: str):
        """获取缓存"""
        if cache_key in cls._cache:
            cached_data, cached_time = cls._cache[cache_key]
            if datetime.now() - cached_time < cls._cache_ttl:
                return cached_data
            else:
                # 缓存过期，删除
                del cls._cache[cache_key]
        return None
    
    @classmethod
    def set(cls, cache_key: str, data: dict):
        """设置缓存"""
        cls._cache[cache_key] = (data, datetime.now())
```

**缓存作用**：
1. **减少外部API调用**：相同查询在缓存有效期内直接返回缓存结果，避免重复调用外部系统
2. **提升响应速度**：缓存命中时响应时间从2秒降低到<50ms
3. **降低外部系统压力**：减少对外部系统的请求频率，避免触发限流
4. **提升用户体验**：用户重复输入相同值时，可以立即获得结果
5. **节省网络资源**：减少网络请求，节省带宽

**缓存失效场景**：
- 缓存过期（TTL 到期）
- Token 通过「接收 Token 接口」重新写入后，可覆盖原缓存（或按需清除查询结果缓存）
- 手动清除缓存（运维/管理员操作，若有提供）

### 3.6 前端交互设计

#### 3.6.1 触发时机
- **失焦触发**：字段失去焦点时立即触发
- **停止输入触发**：检测到用户停止输入超过2秒后自动触发
- 两种触发方式可以同时启用，满足不同用户习惯

**实现示例**：
```typescript
// 失焦触发
onBlur={() => {
  handleAutoFill(fieldValue);
}}

// 停止输入触发（2秒防抖）
const debouncedAutoFill = useMemo(
  () => debounce((value: string) => {
    if (value) {
      handleAutoFill(value);
    }
  }, 2000),  // 2秒延迟
  []
);

onChange={(e) => {
  const value = e.target.value;
  setFieldValue(value);
  debouncedAutoFill(value);  // 停止输入2秒后触发
}}
```

#### 3.6.2 交互流程
1. 用户输入关键字段值
2. **触发条件检查**：
   - 字段值长度 >= 最小长度（默认2个字符）
   - 字段值不为空且不全是空格
   - 如果条件不满足，不触发请求
3. 触发条件满足时显示加载状态（字段旁边显示loading图标）
4. 发送请求到后端
5. 收到响应后：
   - **如果匹配成功（返回1条数据）**：
     - 前端进行字段匹配：将外部系统返回的字段名与模板字段名进行匹配
     - 前端进行类型转换：根据模板字段类型进行相应的类型转换（见3.6.4节）
     - 自动填充所有匹配字段，显示提示"已自动填充X个字段"
   - **如果未匹配到数据（返回0条）**：显示提示"未找到匹配记录"
   - **如果字段值过短**：显示提示"请输入至少X个字符"
   - **如果发生错误**：显示错误提示（如Token过期、网络错误等）
6. 用户确认或修改填充的值

**触发条件限制实现**：
```typescript
const MIN_FIELD_LENGTH = 2;  // 最小字段长度（可配置）

const handleAutoFill = (fieldValue: string) => {
  // 检查字段值长度
  const trimmedValue = fieldValue.trim();
  if (trimmedValue.length < MIN_FIELD_LENGTH) {
    message.warning(`请输入至少${MIN_FIELD_LENGTH}个字符`);
    return;
  }
  
  // 发送请求
  callAutoFillAPI(fieldValue);
};
```

#### 3.6.3 触发条件限制和防抖处理

**触发条件限制**：
- 字段值长度必须 >= `min_field_length`（默认2个字符，可在模板配置中设置）
- 字段值去除首尾空格后不能为空
- 字段值过短时不发送请求，避免无效调用

**防抖处理**：
- 停止输入触发使用2秒防抖，避免用户输入过程中频繁请求
- 失焦触发不需要防抖，直接触发（但仍需检查字段值长度）

**实现逻辑**：
```typescript
// 检查是否满足触发条件
const shouldTriggerAutoFill = (value: string, minLength: number = 2): boolean => {
  const trimmed = value.trim();
  return trimmed.length >= minLength;
};

// 失焦触发（带条件检查）
onBlur={() => {
  if (shouldTriggerAutoFill(fieldValue, minFieldLength)) {
    handleAutoFill(fieldValue);
  }
}}

// 停止输入触发（带条件检查和防抖）
const debouncedAutoFill = useMemo(
  () => debounce((value: string) => {
    if (shouldTriggerAutoFill(value, minFieldLength)) {
      handleAutoFill(value);
    }
  }, 2000),
  [minFieldLength]
);
```

#### 3.6.4 前端字段匹配和类型转换

**实现前必读**：类型转换规则必须与**当前项目中模板字段的实际类型与格式**一致。实现前请查阅：
- 后端：`app/models/field.py` 中 `Field.type` 的取值及约定
- 前端：`TemplateForm` 中字段类型选项（如 input、textarea、number、select、radio、checkbox、date、datetime）及 `LedgerForm` 中各类表单项的取值格式（如日期使用 dayjs、数字为 number、多选为数组等）
- 据此确定每种类型的输入/展示格式（如 date 是否为 `YYYY-MM-DD`、datetime 是否带时分秒等），再实现转换逻辑

**字段匹配逻辑**：
1. 前端获取模板的所有字段配置（字段名、字段类型等）
2. 将外部系统返回的数据字段名与模板字段名进行匹配
3. 如果字段名完全匹配（或经映射后匹配），则按该字段的类型进行转换并填充

**字段映射配置（可选）**：
如果外部系统字段名与模板字段名不一致，可以在模板的`auto_fill_config`中配置字段映射：

```json
{
  "auto_fill_config": {
    "enabled": true,
    "key_field_name": "设备编号",
    "field_mapping": {  // 字段映射配置（可选）
      "device_name": "设备名称",  // 外部系统字段名 -> 模板字段名
      "device_model": "设备型号",
      "supplier": "供应商",
      "purchase_date": "购买日期"
    }
  }
}
```

**类型转换规则（参考）**：
下表为常见类型的参考；**具体规则与格式以当前代码中模板字段类型及表单控件约定为准**，实现时需对照 `Field` 模型与前端表单组件：

| 模板字段类型 | 转换规则（参考） | 示例（格式以现网为准） |
|------------|-----------------|------------------------|
| `input`（单行文本） | 转为字符串 | `"设备A"` → `"设备A"` |
| `textarea`（多行文本） | 转为字符串 | `"描述信息"` → `"描述信息"` |
| `number`（数字） | 转为数字类型 | `"123.45"` → `123.45` |
| `date`（日期） | 按前端日期控件约定格式（如 YYYY-MM-DD 或 dayjs） | 需查阅 LedgerForm 中 DatePicker 的 value 格式 |
| `datetime`（日期时间） | 按前端日期时间控件约定格式 | 需查阅现网约定 |
| `select`（下拉选择） | 值需在选项列表中，否则可不填充或忽略 | `"选项A"` → `"选项A"`（若选项存在） |
| `radio`（单选） | 同 select | 同 select |
| `checkbox`（多选） | 转为数组，与选项一致 | `["选项A", "选项B"]` → `["选项A", "选项B"]` |

**类型转换实现示例**：
```typescript
// 字段匹配和类型转换函数
const matchAndConvertFields = (
  rawData: Record<string, any>,
  templateFields: Field[],
  fieldMapping?: Record<string, string>
): Record<string, any> => {
  const result: Record<string, any> = {};
  
  templateFields.forEach(field => {
    // 获取外部系统的字段名（如果有映射则使用映射，否则使用模板字段名）
    const externalFieldName = fieldMapping?.[field.name] || field.name;
    
    // 检查外部数据中是否存在该字段
    if (rawData.hasOwnProperty(externalFieldName)) {
      const rawValue = rawData[externalFieldName];
      
      // 根据字段类型进行转换
      switch (field.type) {
        case 'input':
        case 'textarea':
          result[field.name] = String(rawValue);
          break;
          
        case 'number':
          result[field.name] = Number(rawValue);
          break;
          
        case 'date':
          // 将各种日期格式转换为 YYYY-MM-DD
          result[field.name] = formatDate(rawValue, 'YYYY-MM-DD');
          break;
          
        case 'datetime':
          // 将各种日期时间格式转换为 YYYY-MM-DD HH:mm:ss
          result[field.name] = formatDateTime(rawValue, 'YYYY-MM-DD HH:mm:ss');
          break;
          
        case 'select':
        case 'radio':
          // 检查值是否在选项中
          if (field.options && field.options.includes(String(rawValue))) {
            result[field.name] = String(rawValue);
          }
          break;
          
        case 'checkbox':
          // 转换为数组
          result[field.name] = Array.isArray(rawValue) ? rawValue : [rawValue];
          break;
          
        default:
          result[field.name] = rawValue;
      }
    }
  });
  
  return result;
};

// 日期格式化辅助函数
const formatDate = (dateValue: any, format: string): string => {
  if (!dateValue) return '';
  
  const date = new Date(dateValue);
  if (isNaN(date.getTime())) return String(dateValue);
  
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  
  return format.replace('YYYY', String(year))
               .replace('MM', month)
               .replace('DD', day);
};

// 日期时间格式化辅助函数
const formatDateTime = (dateValue: any, format: string): string => {
  if (!dateValue) return '';
  
  const date = new Date(dateValue);
  if (isNaN(date.getTime())) return String(dateValue);
  
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  
  return format.replace('YYYY', String(year))
               .replace('MM', month)
               .replace('DD', day)
               .replace('HH', hours)
               .replace('mm', minutes)
               .replace('ss', seconds);
};
```

## 4. 实现步骤

### 阶段1：基础功能实现
1. 采用配置形式维护唯一外部系统（API 地址、request_config、备用 Token 用户号等），不建 external_systems 表
2. 实现「接收 Token 接口」：接收用户号与 Token，写入缓存；不实现 Token 的 GET/查询/删除接口
3. 实现从缓存取 Token 的逻辑：按当前用户 → 备用用户（配置中的 backup_token_user_id）顺序取值
4. 实现外部 API 调用服务（从配置读取请求参数与响应路径）
5. 实现数据提取逻辑（支持单条或 0 条记录返回）
6. 创建自动填充 API 接口（含字段值长度验证，内部使用上述 Token 与外部系统配置）
7. 前端集成自动填充功能（失焦 + 停止输入 2 秒触发，字段值长度检查；类型转换实现前查阅模板字段类型与格式）

### 阶段2：功能增强
1. 添加匹配建议功能（模糊搜索）
2. 添加自动填充历史记录（可选）
3. 支持在管理端展示/编辑单条外部系统配置（仍为配置形式）
4. 支持自定义最小字段长度（按模板或字段配置）
5. 优化字段映射配置的用户体验

### 阶段3：性能优化和监控
1. 添加请求结果缓存
2. 优化外部API调用（连接池、重试）
3. 添加性能监控和统计
4. 添加Token过期提醒
5. 支持批量查询优化

## 5. 数据模型设计和配置文件位置

### 5.1 配置方案概述

**外部系统**：仅有一个外部系统，采用**配置形式**（如环境变量 + 配置文件或单条配置存储），不采用「多外部系统表」的设计。

**配置分类**：
1. **外部系统连接与请求配置**：通过配置指定（如 `config.py`、`.env` 或配置中心），包含 API 地址、请求方法、`request_config`（请求参数模板、响应路径等）
2. **备用 Token 用户**：通过配置指定「备用 Token 对应用的用户号/地址」（如 `backup_token_user_id`），该用户的 Token 由上游通过「接收 Token 接口」写入缓存，当当前用户无 Token 时使用
3. **Token**：不落库，仅存于缓存；通过「接收 Token 接口」写入（用户号 + Token）
4. **模板自动填充配置**：存储在`templates`表的`auto_fill_config`字段（JSON 格式），如是否启用、关键字段名、触发方式、字段映射等

**配置存储方式**：
- 外部系统相关（单系统）：配置文件或单条配置项，便于部署与环境隔离
- 模板自动填充：可继续存于数据库 `templates.auto_fill_config`，便于按模板动态调整

### 5.2 外部系统配置（单一配置形式）

外部系统仅有一个，采用配置形式（如配置文件或环境变量），示例结构如下（具体键名与存储方式可按项目约定）：

```yaml
# 示例：配置文件中的外部系统配置
AUTO_FILL_EXTERNAL_SYSTEM:
  name: "设备管理系统"
  api_base_url: "https://api.example.com"
  api_endpoint: "/api/devices/search"
  request_method: "GET"
  request_config:
    headers: { "Content-Type": "application/json" }
    params: { "device_code": "{field_value}", "include_details": "true" }
    response_path: "data.devices"
    timeout: 5
    retry_times: 3
  # 备用 Token 对应用的用户号（该用户的 Token 由「接收 Token 接口」写入缓存）
  backup_token_user_id: "system_backup_user"
```

或使用环境变量 + JSON 等方式；实现时从配置读取，不建 `external_systems` 表。

**`request_config` 格式（与现设计一致，存于上述配置中）**：
```json
{
  "headers": {  // 自定义请求头（可选，Token会自动添加到Authorization头）
    "Content-Type": "application/json",
    "X-Custom-Header": "value"
  },
  "params": {  // GET请求参数模板（使用{field_value}占位符）
    "device_code": "{field_value}",
    "page": "1",
    "page_size": "10"
  },
  "body": {  // POST请求体模板（使用{field_value}占位符）
    "query": {
      "code": "{field_value}"
    },
    "filters": {}
  },
  "response_path": "data.items",  // 响应数据路径（支持点号分隔的嵌套路径，如"data.items"或"result.list"）
  "timeout": 5,  // 超时时间（秒，默认5秒）
  "retry_times": 3  // 重试次数（默认3次）
}
```

**配置示例**：

**示例1：GET请求配置**
```json
{
  "headers": {
    "Content-Type": "application/json"
  },
  "params": {
    "device_code": "{field_value}",
    "include_details": "true"
  },
  "response_path": "data.devices",
  "timeout": 5,
  "retry_times": 3
}
```

**示例2：POST请求配置**
```json
{
  "headers": {
    "Content-Type": "application/json",
    "X-API-Version": "v1"
  },
  "body": {
    "query": {
      "code": "{field_value}",
      "exact_match": true
    },
    "options": {
      "include_related": true
    }
  },
  "response_path": "result.items",
  "timeout": 8,
  "retry_times": 2
}
```

**配置管理**：通过修改配置文件或配置中心更新，无需单独的「外部系统 CRUD」接口（若需管理界面，可做只读展示或单条配置的编辑，仍不建多系统表）。

**Token**：不建 Token 表。Token 仅通过「接收 Token 接口」写入缓存，键可为「用户号」或「user_id」，值存 Token；备用 Token 从配置的 `backup_token_user_id` 对应用户的缓存项读取。

### 5.3 Template 模型扩展

```python
class Template(Base):
    # ... 现有字段 ...
    
    # 新增字段（外部系统唯一，由全局配置指定，模板不再关联 external_system_id）
    auto_fill_config = Column(JSON, nullable=True)  # 自动填充配置（存储在数据库中）
```

**`auto_fill_config`字段格式（存储在数据库中）**：
```json
{
  "enabled": true,  // 是否启用自动填充
  "key_field_name": "设备编号",  // 触发匹配的关键字段名
  "trigger_on": ["blur", "input"],  // 触发方式：blur（失焦）, input（停止输入）
  "debounce_ms": 2000,  // 停止输入触发的防抖时间（毫秒）
  "min_field_length": 2,  // 最小字段长度，低于此长度不触发自动填充
  "field_mapping": {  // 字段映射配置（可选，如果外部系统字段名与模板字段名不一致）
    "device_name": "设备名称",  // 外部系统字段名 -> 模板字段名
    "device_model": "设备型号",
    "supplier": "供应商",
    "purchase_date": "购买日期"
  }
}
```

**配置说明**：
- `enabled`: 是否启用自动填充功能
- `key_field_name`: 触发自动填充的关键字段名（必须与模板中的字段名一致）
- `trigger_on`: 触发方式数组，支持`blur`（失焦）和`input`（停止输入）
- `debounce_ms`: 停止输入触发的防抖时间（仅对`input`触发方式有效）
- `min_field_length`: 最小字段长度，低于此长度不触发自动填充
- `field_mapping`: 字段映射配置（可选），用于映射外部系统字段名到模板字段名

### 5.4 Field模型扩展

```python
class Field(Base):
    # ... 现有字段 ...
    # 不需要额外字段，直接使用字段名匹配外部系统返回的数据
    # 外部系统返回的数据字段名应该与模板字段名一致，或由管理员在request_config中配置转换规则
```

### 5.5 自动填充历史表（可选，用于统计和调试）

```python
class AutoFillHistory(Base):
    __tablename__ = "auto_fill_history"
    
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("templates.id"))
    field_name = Column(String)
    field_value = Column(String)
    external_record_id = Column(String)  # 外部系统中的记录ID
    matched_data = Column(JSON)  # 匹配到的数据
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    response_time_ms = Column(Integer)  # 响应时间（毫秒）
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

## 6. 安全性考虑

1. **Token 安全**：
   - Token 仅存于缓存，不落库，不提供任何查询或直接访问接口
   - Token 仅能通过「接收 Token 接口」写入（请求体含用户号与 Token），建议对该接口做鉴权（如密钥、IP 白名单）
   - 仅当台账用户调用自动填充接口时，后端在内部从缓存按「先用户、后备用」取 Token 使用

2. **权限控制**：
   - 只有有权限创建/编辑台账的用户才能使用自动填充接口
   - 无人可通过台账系统直接读取或导出 Token

3. **API 安全**：
   - 验证外部系统API地址白名单
   - 防止SSRF攻击（限制请求的目标地址）
   - 请求参数验证和清理
   - 响应数据验证和过滤

4. **数据安全**：
   - 敏感字段不参与自动填充（可在配置中排除）
   - 传输数据加密（HTTPS）
   - 记录所有自动填充操作日志

5. **错误处理**：
   - 不暴露 Token 信息给前端（且无接口可查询 Token）
   - 统一错误响应格式
   - 记录错误日志便于排查

## 7. 性能指标

- **响应时间**：< 2秒（P95，包含外部API调用）
- **匹配准确率**：> 95%（基于外部系统数据）
- **Token有效性**：> 99%
- **外部API可用性**：> 99.5%
- **并发支持**：支持50+并发请求（受外部系统限制）
- **缓存命中率**：> 40%（针对重复查询）

## 8. 扩展性考虑

1. **外部系统**：当前设计为单一外部系统、配置形式；若未来需多系统，可在配置中扩展为列表或再引入数据模型
2. **多种认证方式**：支持 Bearer、API Key 等，Token 由接收接口写入缓存
3. **数据转换**：类型转换以当前模板字段类型与格式为准，实现前查阅代码；后续可考虑可插拔转换规则
4. **Webhook 支持**：支持外部系统主动推送数据更新（可选）
5. **规则引擎**：支持复杂的数据转换和匹配规则配置（可选）
6. **数据同步**：可选的数据同步功能，定期同步外部系统数据到本地缓存

## 9. 测试策略

1. **单元测试**：测试匹配逻辑
2. **集成测试**：测试API接口
3. **性能测试**：测试查询性能
4. **用户体验测试**：测试前端交互

## 10. 实现细节

### 10.1 外部 API 调用服务（配置形式，Token 来自缓存）

外部系统唯一，从配置读取；Token 由调用方从缓存按「先当前用户、再 backup_token_user_id」取得后传入。

```python
import httpx
from typing import Dict, Any, List, Optional
import json

def get_token_for_auto_fill(current_user_id: str, cache, config) -> Optional[str]:
    """先从缓存取当前用户 Token，无则取配置的备用用户 Token。"""
    token = cache.get(f"auto_fill:token:{current_user_id}")
    if token:
        return token
    backup_user_id = config.get("AUTO_FILL_EXTERNAL_SYSTEM", {}).get("backup_token_user_id")
    if backup_user_id:
        return cache.get(f"auto_fill:token:{backup_user_id}")
    return None

class ExternalSystemService:
    @staticmethod
    def call_external_api(
        system_config: dict,  # 从配置读取的单一外部系统配置
        token: str,
        field_value: str
    ) -> List[Dict[str, Any]]:
        """
        调用外部系统 API（高度可配置）
        配置从配置项读取（如 AUTO_FILL_EXTERNAL_SYSTEM）
        只做数据提取和基本格式化，不进行字段匹配和类型转换
        """
        url = f"{system_config['api_base_url']}{system_config['api_endpoint']}"
        config = system_config.get("request_config", {})
        
        # 构建请求头（支持自定义）
        headers = {
            "Authorization": f"Bearer {token}",
            **config.get("headers", {})  # 合并自定义请求头
        }
        
        # 替换占位符 {field_value}
        def replace_placeholder(obj, value: str):
            """递归替换占位符"""
            if isinstance(obj, dict):
                return {k: replace_placeholder(v, value) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_placeholder(item, value) for item in obj]
            elif isinstance(obj, str):
                return obj.replace("{field_value}", value)
            else:
                return obj
        
        timeout = config.get("timeout", 5)
        retry_times = config.get("retry_times", 3)
        request_method = system_config.get("request_method", "GET").upper()
        
        # 发送请求（支持重试）
        for attempt in range(retry_times):
            try:
                with httpx.Client(timeout=timeout) as client:
                    if request_method == "GET":
                        # GET请求：使用params
                        params = replace_placeholder(config.get("params", {}), field_value)
                        response = client.get(url, params=params, headers=headers)
                    elif request_method == "POST":
                        # POST请求：使用body
                        body = replace_placeholder(config.get("body", {}), field_value)
                        response = client.post(url, json=body, headers=headers)
                    else:
                        # 支持PUT等其他方法
                        body = replace_placeholder(config.get("body", {}), field_value)
                        response = client.request(request_method, url, json=body, headers=headers)
                    
                    response.raise_for_status()
                    response_data = response.json()
                    
                    # 提取响应数据（支持嵌套路径）
                    response_path = config.get("response_path", "")
                    if response_path:
                        extracted_data = DataExtractionService.extract_response_data(
                            response_data, response_path
                        )
                    else:
                        # 如果没有配置路径，直接使用响应数据
                        extracted_data = response_data if isinstance(response_data, list) else [response_data]
                    
                    # 外部系统一般只返回0条或1条数据，如果返回多条，只取第一条
                    if len(extracted_data) > 1:
                        extracted_data = [extracted_data[0]]
                    
                    # 返回原始数据，不进行字段匹配和类型转换
                    return extracted_data
                    
            except httpx.TimeoutException:
                if attempt == retry_times - 1:
                    raise Exception("外部API请求超时")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise Exception("Token无效或已过期")
                raise
        
        return []
```

### 10.2 数据提取服务（后端只做粗加工）

```python
class DataExtractionService:
    @staticmethod
    def extract_response_data(
        response_data: Dict[str, Any],
        response_path: str
    ) -> List[Dict[str, Any]]:
        """
        从响应中提取数据（支持嵌套路径）
        只做数据提取，不进行字段匹配和类型转换
        注意：外部系统一般只返回0条或1条数据，如果返回多条，调用方应只取第一条
        """
        # 支持点号分隔的路径，如 "data.items" 或 "result.list"
        if not response_path:
            # 如果没有配置路径，直接使用响应数据
            if isinstance(response_data, list):
                return response_data
            elif isinstance(response_data, dict):
                return [response_data]
            else:
                return []
        
        parts = response_path.split('.')
        current = response_data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return []
        
        # 确保返回列表格式
        if isinstance(current, list):
            return current
        elif isinstance(current, dict):
            return [current]
        else:
            return []
    
    @staticmethod
    def validate_field_value(
        field_value: str,
        min_length: int = 2
    ) -> tuple[bool, Optional[str]]:
        """
        验证字段值是否满足触发条件
        返回: (是否有效, 错误信息)
        """
        if not field_value:
            return False, "字段值不能为空"
        
        trimmed = field_value.strip()
        if len(trimmed) < min_length:
            return False, f"字段值过短，请输入至少{min_length}个字符"
        
        return True, None
```

### 10.3 配置文件管理

**配置存储位置总结**：

1. **外部系统配置**（唯一，配置形式）
   - **存储位置**：配置文件或配置中心（如 `config.py`、`.env` 或 YAML）
   - **包含内容**：
     - `name`、`api_base_url`、`api_endpoint`、`request_method`
     - `request_config`：`headers`、`params`/`body`、`response_path`、`timeout`、`retry_times`
     - `backup_token_user_id`：备用 Token 对应用户号，该用户 Token 通过「接收 Token 接口」写入缓存
   - **管理方式**：修改配置文件或配置中心，无需多系统表

2. **Token**
   - **存储位置**：仅缓存（如 Redis 或应用内存），不落库
   - **写入方式**：通过「接收 Token 接口」传入用户号与 Token，写入缓存
   - **使用方式**：仅自动填充调用链内部使用，先取当前用户 Token，无则取备用用户 Token；不提供任何查询/直接访问接口

3. **模板自动填充配置** (`auto_fill_config`)
   - **存储位置**：`templates`表的`auto_fill_config`字段（JSON类型）
   - **包含内容**：
     - `enabled`: 是否启用
     - `key_field_name`: 关键字段名
     - `trigger_on`: 触发方式
     - `debounce_ms`: 防抖时间
     - `min_field_length`: 最小字段长度
     - `field_mapping`: 字段映射配置（可选）
   - **管理方式**：通过模板管理接口进行更新

**配置访问流程**：
```
前端请求自动填充
  ↓
后端读取模板的 auto_fill_config
  ↓
后端从配置读取唯一外部系统（request_config 等）
  ↓
后端从缓存取 Token（先当前用户，无则 backup_token_user_id 对应用户）
  ↓
后端使用配置与 Token 调用外部系统 API
  ↓
后端返回原始数据给前端
  ↓
前端按模板字段类型与格式进行匹配和类型转换（实现前查阅现有字段定义）
```

## 11. 后续优化方向

1. **智能推荐**：基于用户历史行为推荐匹配结果
2. **批量导入**：支持Excel批量导入时自动匹配
3. **数据质量**：识别和标记数据质量问题
4. **统计分析**：统计匹配成功率、常用字段、外部系统调用情况等
5. **Token自动刷新**：实现Token自动刷新机制
6. **多系统优先级**：支持配置多个外部系统，按优先级查询




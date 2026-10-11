# ThaiJO plugin for Claude

ปลั๊กอิน (MCP server) สำหรับค้นหางานวิจัยทุกฉบับใน [ThaiJO](https://www.tci-thaijo.org) (Thai Journals Online, 400,000+ บทความ) จาก Claude

## เครื่องมือ

| Tool | ใช้ทำอะไร |
|---|---|
| `search_articles` | ค้นบทความทุกวารสาร (ไทย/อังกฤษ) กรองตามปี, ภาษา, วารสาร, สาขา, ฟิลด์ (ชื่อเรื่อง/บทคัดย่อ/ผู้แต่ง/คำสำคัญ/DOI), เรียงลำดับ, แบ่งหน้า (สูงสุด 50 รายการ/หน้า) |
| `get_article` | ดูรายละเอียดบทความ: บทคัดย่อ, ผู้แต่ง, คำสำคัญ, หน้า, DOI, ลิงก์ PDF |
| `search_journals` | ค้นวารสาร ได้ path, ISSN, TCI tier |
| `list_subject_groups` | รายการกลุ่มสาขาและรหัส category |

## ติดตั้ง

ต้องมี [uv](https://docs.astral.sh/uv/)

**Claude Code (แบบ plugin):**
```
/plugin marketplace add popwerasak/-
/plugin install thaijo@thaijo-marketplace
```

**Claude Code (เปิดในโฟลเดอร์ repo นี้):** `.mcp.json` จะโหลด server `thaijo` ให้อัตโนมัติ

**Claude Desktop:** เพิ่มใน `claude_desktop_config.json`
```json
{
  "mcpServers": {
    "thaijo": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/this/repo", "thaijo-mcp"]
    }
  }
}
```

## ตัวอย่างคำสั่ง

- "ค้นงานวิจัยเรื่องเบาหวานในผู้สูงอายุ ปี 2020-2025 จาก ThaiJO"
- "หาบทความ machine learning ภาษาอังกฤษ เรียงจากใหม่ไปเก่า แล้วสรุปบทคัดย่อ 5 เรื่องแรก"
- "วารสารพยาบาลที่อยู่ TCI tier 1 มีอะไรบ้าง"

ใช้ API สาธารณะของเว็บไซต์ ThaiJO (`https://www.tci-thaijo.org/api/v1`)

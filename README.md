# JKT48 Daily Schedule Retrieval
Retrieve JKT48 schedules daily and compress it into a .json file and serve it into github pages.

### Purpose
To be the "backend" for jkt48-theatre-recap-ext (On progress)

### Data Scope
- JKT48 schedules are scraped only if:
  1. type == "SHOW"
  2. type == "EVENT" && is_in_theater == true
- The data are then grouped based on the month that they are in (**the format is YYYY-mm**).

### How to use
`fetch` the data from `https://lostasf.github.io/jkt48/api/data/schedules/{YYYY-MM}.json`. 
Example: `https://lostasf.github.io/jkt48/api/data/schedules/2026-04.json`

### Data Structure
```
{
  "members": {
    "33": "Aurhel Alana", // member_id: member_name
    "114": "Hillary Abigail"
  },
  "schedules": [
    [
      487,
      "OEV-523",
      "ANDAI \u2018KU BUKAN IDOLA",
      1772730000,
      "E",
      [17,26,48,59,64,67,91,94,97,115,120,127,148,159,161,166]
    ],
    [
      3128,
      "SH8CD7",
      "Pertaruhan Cinta",
      1774976400,
      "S",
      [22,26,46,48,64,67,88,94,97,148,152,159]
    ]
  ]
}
```
Table explaining what the data means:
| Category  | Data                                                     | Meaning                                        |
|-----------|----------------------------------------------------------|------------------------------------------------|
| members   | "33"                                                     | member_id                                      |
| members   | "Aurhel Alana"                                           | member_name                                    |
| schedules | "487"                                                    | schedule_id                                    |
| schedules | "OEV-523"                                                | reference_code                                 |
| schedules | "ANDAI \u2018KU BUKAN IDOLA"                             | title                                          |
| schedules | 1772730000                                               | date                                           |
| schedules | "E"                                                      | "E" -> type == "EVENT" - "S" -> type == "SHOW" |
| schedules | [17,26,48,59,64,67,91,94,97,115,120,127,148,159,161,166] | Array of member_id's                           |

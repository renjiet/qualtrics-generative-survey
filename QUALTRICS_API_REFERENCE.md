# Qualtrics Survey API Reference

> Scraped from https://api.qualtrics.com/ on 2026-03-05. API version: v3.0.0

---

## Authentication

Two methods supported:

1. **API Key** — Include header `X-API-TOKEN: <your_token>`
2. **OAuth 2.0**

Get your API token from: Qualtrics Account Settings > Qualtrics IDs

---

## Base URLs (by Data Center)

| Data Center | Base URL |
|---|---|
| Canadian | `https://yul1.qualtrics.com/API/v3` |
| Washington DC (previously CO1) | `https://iad1.qualtrics.com/API/v3` |
| Portland OR (previously AZ/SJC) | `https://pdx1.qualtrics.com/API/v3` |
| EU (previously EU2/EU) | `https://fra1.qualtrics.com/API/v3` |
| London UK | `https://lhr1.qualtrics.com/API/v3` |
| Sydney AU (previously AU1) | `https://syd1.qualtrics.com/API/v3` |
| Singapore | `https://sin1.qualtrics.com/API/v3` |
| Tokyo JP | `https://hnd1.qualtrics.com/API/v3` |
| US Government | `https://gov1.qualtrics.com/API/v3` |
| Mock Server | `https://stoplight.io/mocks/qualtricsv2/publicapidocs/60936` |

**Important:** Old data center codes (e.g., `co1`, `az1`, `au1`, `eu`) have been replaced with the city-based codes above.

---

## Common Headers

```
Content-Type: application/json
Accept: application/json
X-API-TOKEN: <your_token>
```

---

## ID Patterns

| Entity | Pattern | Example |
|---|---|---|
| Survey | `^SV_[a-zA-Z0-9]{11,15}$` | `SV_abc123def456g` |
| Block | `^BL_[a-zA-Z0-9]{11,15}$` | `BL_abc123def456g` |
| Question | `^QID[a-zA-Z0-9]+$` | `QID1`, `QID23` |
| Flow | `^FL_[1-9][0-9]*$` | `FL_1`, `FL_12` |

---

## Survey Questions API

### List All Questions

```
GET /survey-definitions/{surveyId}/questions
```

### Get Single Question

```
GET /survey-definitions/{surveyId}/questions/{questionId}
```

### Create Question

```
POST /survey-definitions/{surveyId}/questions
```

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `blockId` | string | No | Block to add the question to. Pattern: `^BL_[a-zA-Z0-9]{11,15}$`. If omitted, adds to the default block. |

**Request Body (Multiple Choice example):**

```json
{
  "ChoiceOrder": ["1", "2"],
  "Choices": {
    "1": { "Display": "choice 1" },
    "2": { "Display": "choice 2" }
  },
  "Configuration": {
    "QuestionDescriptionOption": "UseText",
    "TextPosition": "inline",
    "ChoiceColumnWidth": 25,
    "RepeatHeaders": "none",
    "WhiteSpace": "ON",
    "LabelPosition": "BELOW",
    "NumColumns": 0,
    "MobileFirst": true
  },
  "DataExportTag": "Q1",
  "Language": [],
  "NextAnswerId": 0,
  "NextChoiceId": 0,
  "QuestionDescription": "my_variable_name",
  "QuestionID": "QID1",
  "QuestionText": "What is your preference?",
  "QuestionType": "MC",
  "Randomization": "string",
  "RecodeValues": {
    "1": "1",
    "2": "2"
  },
  "Selector": "SAVR",
  "SubSelector": "TX",
  "Validation": {
    "Settings": {
      "ForceResponse": "OFF",
      "ForceResponseType": "OFF",
      "Type": "None"
    }
  }
}
```

**Response (200):**

```json
{
  "meta": {
    "httpStatus": "200 - OK",
    "requestId": "...",
    "notice": "..."
  },
  "result": {
    "QuestionID": "QID1"
  }
}
```

### Update Question

```
PUT /survey-definitions/{surveyId}/questions/{questionId}
```

Same body schema as Create Question.

### Delete Question

```
DELETE /survey-definitions/{surveyId}/questions/{questionId}
```

---

## Required Fields for Create/Update Question

| Field | Type | Required | Description |
|---|---|---|---|
| `ChoiceOrder` | array[string] | Yes | Order of choices, e.g. `["1", "2", "3"]` |
| `Choices` | object | Yes | Choice definitions. Keys are string numbers, values have `Display` key |
| `Configuration` | object | Yes | Display configuration (see below) |
| `Language` | array or object | Yes | Translations. Use `[]` for default |
| `QuestionDescription` | string | Yes | Label/variable name for the question |
| `QuestionText` | string | Yes | The question text shown to respondents (0-1000 chars) |
| `QuestionType` | string | Yes | Question type (see types below) |
| `Selector` | string | Yes | Response format selector |
| `SubSelector` | string | Yes | Refines the selector |
| `Validation` | object | Yes | Validation settings |

### Optional Fields

| Field | Type | Description |
|---|---|---|
| `DataExportTag` | string | Tag for exported data |
| `NextAnswerId` | integer | Next answer ID counter |
| `NextChoiceId` | integer | Next choice ID counter |
| `QuestionID` | string | Custom question ID (pattern: `^QID[a-zA-Z0-9]+$`) |
| `Randomization` | string/object | Choice randomization settings |
| `RecodeValues` | object | Numeric recode mapping, e.g. `{"1": "1", "2": "2", "3": "-1000"}` |

---

## QuestionType Values

The API documentation shows `MC` (Multiple Choice) as the primary documented type. Based on Qualtrics survey structure, the supported types include:

| QuestionType | Description |
|---|---|
| `MC` | Multiple Choice |
| `Matrix` | Matrix Table |
| `TE` | Text Entry |
| `DB` | Descriptive Text / Graphic |
| `Slider` | Slider |
| `RO` | Rank Order |
| `CS` | Constant Sum |
| `SBS` | Side by Side |
| `DD` | Drill Down |
| `HotSpot` | Hot Spot |
| `GAP` | Gap Analysis |
| `Meta` | Meta Info Question |
| `Timing` | Timing |

---

## Selector Values (for MC questions)

| Selector | Description |
|---|---|
| `DL` | Dropdown List |
| `GRB` | Graphic Radio Buttons |
| `MACOL` | Multiple Answer Column |
| `MAHR` | Multiple Answer Horizontal |
| `MAVR` | Multiple Answer Vertical |
| `MSB` | Multi Select Box |
| `NPS` | Net Promoter Score |
| `SACOL` | Single Answer Column |
| `SAHR` | Single Answer Horizontal |
| `SAVR` | Single Answer Vertical |
| `SB` | Select Box |
| `TB` | Text Box |
| `TXOT` | Text/Other |
| `PTB` | Password Text Box |

---

## SubSelector Values

| SubSelector | Description |
|---|---|
| `GR` | Grid |
| `TX` | Text (default for most MC) |
| `TXOT` | Text with Other option |
| `WOTXB` | Without Text Box |
| `WTXB` | With Text Box |

---

## Configuration Object

| Field | Type | Allowed Values | Description |
|---|---|---|---|
| `QuestionDescriptionOption` | string | `UseText`, `SpecifyLabel` | How description is set |
| `TextPosition` | string | `inline` | Position of question text |
| `ChoiceColumnWidth` | integer | `25` | Column width for choices |
| `RepeatHeaders` | string | `none` | Header repetition |
| `WhiteSpace` | string | `ON`, `OFF` | White space formatting |
| `LabelPosition` | string | `BELOW`, `SIDE` | Label placement |
| `NumColumns` | integer | any | Number of columns for choices |
| `MobileFirst` | boolean | `true`, `false` | Mobile-optimized formatting |

---

## Survey Blocks API

### Create Block

```
POST /survey-definitions/{surveyId}/blocks
```

**Important:** Blocks must be created with an empty `BlockElements` array. Questions are then added to the block using the Create Question endpoint with the `blockId` query parameter.

**Request Body:**

```json
{
  "Type": "Standard",
  "Description": "My Block Name",
  "BlockElements": [],
  "Options": {
    "BlockLocking": "false",
    "RandomizeQuestions": "false",
    "BlockVisibility": "Collapsed"
  }
}
```

**Response (200):**

```json
{
  "meta": {
    "httpStatus": "200 - OK",
    "requestId": "...",
    "notice": "..."
  },
  "result": {
    "BlockID": "BL_abc123def456g",
    "FlowID": "FL_1"
  }
}
```

### Get Block

```
GET /survey-definitions/{surveyId}/blocks/{blockId}
```

### Update Block

```
PUT /survey-definitions/{surveyId}/blocks/{blockId}
```

### Delete Block

```
DELETE /survey-definitions/{surveyId}/blocks/{blockId}
```

### Block Body Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `Type` | string | Yes | `Standard` |
| `SubType` | string | Yes (for Reference blocks) | `Reference` |
| `Description` | string/null | Yes | Block name/description |
| `BlockElements` | array | Yes | Must be `[]` on creation |
| `ID` | string | Yes (for Reference blocks) | Block ID |
| `Options` | object | No | Block options (see below) |

### Block Options

| Field | Type | Values | Description |
|---|---|---|---|
| `BlockLocking` | string | `true`, `false` | Prevent modification |
| `BlockPassword` | string | any | Password to modify |
| `BlockVisibility` | string | `Collapsed`, `Expanded` | Display state |
| `RandomizeQuestions` | string | `false`, `RandomWithXPerPage`, `RandomWithOnlyX`, `Advanced` | Randomization |
| `Looping` | string | `None`, `Static`, `Question` | Loop & Merge type |
| `LoopingOptions` | object | — | Loop configuration |
| `NextButton` | string | any | Custom next button text |
| `PreviousButton` | string | any | Custom previous button text |

---

## Validation Object

```json
{
  "Settings": {
    "ForceResponse": "OFF",
    "ForceResponseType": "OFF",
    "Type": "None"
  }
}
```

For custom validation:

```json
{
  "Settings": {
    "CustomValidation": {
      "Logic": {
        "Type": "BooleanExpression",
        "property1": {
          "ChoiceLocator": "string",
          "LogicType": "Question",
          "Operator": "Selected",
          "QuestionID": "QID1",
          "QuestionIsInLoop": "yes",
          "Type": "Expression"
        }
      },
      "Message": {
        "description": "Please select an option",
        "libraryID": "...",
        "messageID": "...",
        "subMessageID": "VE_FORCE_RESPONSE"
      }
    },
    "ForceResponse": "ON",
    "ForceResponseType": "ON",
    "Type": "CustomValidation"
  }
}
```

---

## Other Survey API Endpoints (under Qualtrics Survey API)

| Category | Endpoints |
|---|---|
| **Surveys** | CRUD operations on surveys |
| **Survey Flows** | Get/Update survey flow logic |
| **Survey Options** | Get/Update survey settings |
| **Survey Versions** | Manage survey versions |
| **Survey Quotas** | Manage response quotas |
| **Survey Languages** | Manage available languages |
| **Survey Translations** | Manage question translations |

---

## Workflow: Creating a Block with Questions

1. **Create a block** (with empty `BlockElements`):
   ```
   POST /survey-definitions/{surveyId}/blocks
   ```
   Returns `BlockID`.

2. **Create questions in that block** (using `blockId` query param):
   ```
   POST /survey-definitions/{surveyId}/questions?blockId={blockId}
   ```

3. **Verify** by getting the block:
   ```
   GET /survey-definitions/{surveyId}/blocks/{blockId}
   ```

---

## Documentation Links

| Page | URL |
|---|---|
| Main API Reference | https://api.qualtrics.com/60d24f6897737-qualtrics-survey-api |
| Create Question | https://api.qualtrics.com/5d41105e8d3b7-create-question |
| Update Question | https://api.qualtrics.com/00d49b25519bb-update-question |
| Get Question | https://api.qualtrics.com/1ebd0bb7008f8-get-question |
| Get Questions | https://api.qualtrics.com/957c5f8a4604b-get-questions |
| Delete Question | https://api.qualtrics.com/cd0302fb06379-delete-question |
| Create Block | https://api.qualtrics.com/2d5286cc34ed6-create-block |
| Get Block | https://api.qualtrics.com/01bfe37616cce-get-block |
| Update Block | https://api.qualtrics.com/54c20622ffd25-update-block |
| Delete Block | https://api.qualtrics.com/4a6ed60352f79-delete-block |
| Finding IDs | https://api.qualtrics.com/ZG9jOjg3NjYzNQ-finding-your-qualtrics-i-ds |

---

## Key Changes from Old API (2024 vs Current)

1. **Data center codes changed**: `co1` -> `iad1`, `az1`/`sjc1` -> `pdx1`, `au1` -> `syd1`, `eu`/`eu2` -> `fra1`. Old codes like `syd1` may still work but the naming convention is now city-based.
2. **Block creation requires empty `BlockElements`**: You can no longer create a block with questions in one call. Create the block first, then add questions via the `?blockId=` query parameter.
3. **OAuth 2.0 support added**: In addition to API key auth.
4. **`SubType` field**: Now required for Reference blocks (value: `"Reference"`). For standard blocks, use `"Type": "Standard"`.
5. **Validation object is required**: Even if no validation, include `{"Settings": {"ForceResponse": "OFF", "ForceResponseType": "OFF", "Type": "None"}}`.

from flask import Flask, render_template, request, jsonify
import requests
import json
import anthropic
import openai

app = Flask(__name__)

SYSTEM_PROMPT = """You are an API assistant that generates Qualtrics question JSON payloads.

Given a natural-language question description, return a COMPLETE JSON object ready for the Qualtrics Create Question API. Output ONLY valid JSON — no markdown fences, no commentary, no extra text.

The JSON must include ALL of these fields:

{
  "ChoiceOrder": ["1", "2", ...],
  "Choices": {"1": {"Display": "..."}, "2": {"Display": "..."}, ...},
  "Configuration": {
    "QuestionDescriptionOption": "SpecifyLabel",
    "TextPosition": "inline",
    "ChoiceColumnWidth": 25,
    "RepeatHeaders": "none",
    "WhiteSpace": "OFF",
    "LabelPosition": "SIDE",
    "NumColumns": 1,
    "MobileFirst": true
  },
  "Language": [],
  "QuestionDescription": "snake_case_variable_name",
  "QuestionText": "The question text shown to respondents",
  "QuestionType": "MC",
  "Selector": "SAVR",
  "SubSelector": "TX",
  "DataExportTag": "snake_case_variable_name",
  "Validation": {
    "Settings": {
      "ForceResponse": "OFF",
      "ForceResponseType": "OFF",
      "Type": "None"
    }
  }
}

Rules:
- QuestionType: Use "MC" for multiple choice, "TE" for text entry, "DB" for descriptive text/graphic.
- For MC questions: Use "SAVR" (single answer vertical) or "MAVR" (multiple answer vertical) as Selector. Use "TX" as SubSelector.
- For TE questions: Use "SL" (single line), "ML" (multi line), or "FORM" as Selector. Do NOT include SubSelector at all for TE questions — omit it entirely. Omit Choices and ChoiceOrder.
- For DB questions: Use "TB" as Selector. Do NOT include SubSelector at all for DB questions — omit it entirely. Omit Choices and ChoiceOrder.
- For Slider questions: QuestionType is "Slider". Use "HBAR" (horizontal bar), "HSLIDER" (horizontal slider), or "STAR" (star rating) as Selector. Do NOT include SubSelector at all for Slider questions — omit it entirely. Use Choices to define the slider labels/items (e.g. {"1": {"Display": "Item 1"}}). Include ChoiceOrder. Include a "Labels" object if the user specifies endpoint labels, e.g. {"Labels": {"1": {"Display": "Not at all"}, "2": {"Display": "Extremely"}}}.
- QuestionDescription and DataExportTag should be a short snake_case variable name capturing the question's meaning.
- If the user specifies choice values or variable names, use them exactly.
- If the user specifies recode values (numbers in parentheses after choices), include a RecodeValues object mapping choice keys to those values.
- Output ONLY the JSON object. No explanation, no markdown."""


def llm_complete(llm_key, llm_provider, system_msg, user_msg, max_tokens=2048):
    """Call either Anthropic or OpenAI and return the text response."""
    if llm_provider == "openai":
        client = openai.OpenAI(api_key=llm_key)
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=max_tokens,
            temperature=0,
        )
        return resp.choices[0].message.content.strip()
    else:
        client = anthropic.Anthropic(api_key=llm_key)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system_msg,
            messages=[{"role": "user", "content": user_msg}],
        )
        return resp.content[0].text.strip()


def strip_markdown_fences(content):
    """Remove markdown code fences if present."""
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    return content


def qualtrics_headers(api_token):
    return {
        "Content-Type": "application/json",
        "X-API-TOKEN": api_token,
    }


def qualtrics_base(data_center, survey_id):
    return f"https://{data_center}.qualtrics.com/API/v3/survey-definitions/{survey_id}"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/survey", methods=["POST"])
def get_survey():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]

    base = qualtrics_base(data_center, survey_id)
    resp = requests.get(base, headers=qualtrics_headers(api_token))
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json())


@app.route("/api/blocks", methods=["POST"])
def list_blocks():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]

    base = qualtrics_base(data_center, survey_id)
    resp = requests.get(base, headers=qualtrics_headers(api_token))
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code

    result = resp.json().get("result", {})
    blocks = result.get("Blocks", {})
    questions = result.get("Questions", {})

    block_list = []
    for block_id, block_data in blocks.items():
        block_questions = []
        for elem in block_data.get("BlockElements", []):
            if elem.get("Type") == "Question":
                qid = elem.get("QuestionID")
                q = questions.get(qid, {})
                validation = q.get("Validation", {}).get("Settings", {})
                force = validation.get("ForceResponse", "OFF")
                block_questions.append({
                    "QuestionID": qid,
                    "QuestionText": q.get("QuestionText", ""),
                    "QuestionType": q.get("QuestionType", ""),
                    "QuestionDescription": q.get("QuestionDescription", ""),
                    "ForceResponse": force,
                })
        block_list.append({
            "BlockID": block_id,
            "Description": block_data.get("Description", ""),
            "Type": block_data.get("Type", ""),
            "QuestionCount": len(block_questions),
            "Questions": block_questions,
        })

    # Also fetch flow for block ordering
    flow_resp = requests.get(f"{base}/flow", headers=qualtrics_headers(api_token))
    flow_data = flow_resp.json().get("result", {}) if flow_resp.status_code == 200 else {}

    return jsonify({"blocks": block_list, "rawBlocks": blocks, "questions": questions, "flow": flow_data})


@app.route("/api/blocks/create", methods=["POST"])
def create_block():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]
    block_name = data["blockName"]

    base = qualtrics_base(data_center, survey_id)
    payload = {
        "Type": "Standard",
        "Description": block_name,
        "BlockElements": [],
    }

    resp = requests.post(f"{base}/blocks", headers=qualtrics_headers(api_token), json=payload)
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json())


@app.route("/api/parse", methods=["POST"])
def parse_question():
    data = request.json
    llm_key = data["llmKey"]
    llm_provider = data.get("llmProvider", "anthropic")
    text = data["text"]

    questions_raw = [q.strip() for q in text.split("---") if q.strip()]
    results = []

    for q_text in questions_raw:
        content = ""
        try:
            content = llm_complete(llm_key, llm_provider, SYSTEM_PROMPT, q_text)
            content = strip_markdown_fences(content)
            parsed = json.loads(content)
            results.append({"success": True, "json": parsed, "input": q_text})
        except json.JSONDecodeError as e:
            results.append({"success": False, "error": f"Invalid JSON from LLM: {e}", "raw": content, "input": q_text})
        except Exception as e:
            results.append({"success": False, "error": str(e), "input": q_text})

    return jsonify({"results": results})


@app.route("/api/submit", methods=["POST"])
def submit_question():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]
    block_id = data.get("blockId")
    question_json = data["questionJson"]

    base = qualtrics_base(data_center, survey_id)
    url = f"{base}/questions"
    if block_id:
        url += f"?blockId={block_id}"

    resp = requests.post(url, headers=qualtrics_headers(api_token), json=question_json)
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json())


@app.route("/api/question/update", methods=["POST"])
def update_question():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]
    question_id = data["questionId"]
    question_json = data["questionJson"]

    base = qualtrics_base(data_center, survey_id)
    url = f"{base}/questions/{question_id}"

    resp = requests.put(url, headers=qualtrics_headers(api_token), json=question_json)

    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json())


@app.route("/api/question/delete", methods=["POST"])
def delete_question():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]
    question_id = data["questionId"]

    base = qualtrics_base(data_center, survey_id)
    url = f"{base}/questions/{question_id}"

    resp = requests.delete(url, headers=qualtrics_headers(api_token))
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json())


@app.route("/api/question/get", methods=["POST"])
def get_question():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]
    question_id = data["questionId"]

    base = qualtrics_base(data_center, survey_id)
    url = f"{base}/questions/{question_id}"

    resp = requests.get(url, headers=qualtrics_headers(api_token))
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code

    return jsonify(resp.json())


DISPLAY_LOGIC_SYSTEM_PROMPT = """You are an expert at generating Qualtrics DisplayLogic JSON.

You will receive:
1. A description of display logic in plain English
2. A summary of available survey questions (QID, description, type, choices)

Return ONLY a valid DisplayLogic JSON object. No markdown fences, no commentary.

### DisplayLogic structure

The top-level object:
{
  "0": { ... group ... },
  "Type": "BooleanExpression",
  "inPage": false
}

Each group has numbered conditions and a Type ("If" for first group, "ElseIf" for subsequent groups used for complex OR with grouping):
"0": {
  "0": { ...condition... },
  "1": { "Conjuction": "And", ...condition... },
  "Type": "If"
}

### Condition for MC (multiple choice) questions
{
  "ChoiceLocator": "q://QID{n}/SelectableChoice/{choiceKey}",
  "Description": "<span class=\\"ConjDesc\\">If</span> <span class=\\"QuestionDesc\\">{description}</span> <span class=\\"LeftOpDesc\\">{choiceDisplay}</span> <span class=\\"OpDesc\\">Is Selected</span>",
  "LeftOperand": "q://QID{n}/SelectableChoice/{choiceKey}",
  "LogicType": "Question",
  "Operator": "Selected",
  "QuestionID": "QID{n}",
  "QuestionIDFromLocator": "QID{n}",
  "QuestionIsInLoop": "no",
  "Type": "Expression"
}
MC operators: "Selected", "NotSelected"

### Condition for TE (text entry) questions
{
  "ChoiceLocator": "q://QID{n}/ChoiceTextEntryValue",
  "Description": "<span class=\\"ConjDesc\\">If</span> <span class=\\"QuestionDesc\\">{description}</span> <span class=\\"OpDesc\\">Is Not Empty</span>",
  "LeftOperand": "q://QID{n}/ChoiceTextEntryValue",
  "LogicType": "Question",
  "Operator": "NotEmpty",
  "QuestionID": "QID{n}",
  "QuestionIDFromLocator": "QID{n}",
  "QuestionIsInLoop": "no",
  "Type": "Expression"
}
TE operators: "Empty", "NotEmpty", "EqualTo", "NotEqualTo", "Contains", "GreaterThan", "LessThan", "GreaterThanOrEqual", "LessThanOrEqual"
Comparison operators require a "RightOperand" field with the value as a string.

### Combining conditions
- AND: Add "Conjuction": "And" to second+ conditions in the same group (note: "Conjuction" is a Qualtrics typo, NOT "Conjunction")
- Simple OR: Add "Conjuction": "Or" to second+ conditions in the same group
- Complex OR with grouping (A AND B) OR C: Use separate groups — first group Type "If", subsequent groups Type "ElseIf"

### Important
- Use exact QIDs and choice keys from the provided survey context
- The Description field must use the HTML span format shown above
- "Conjuction" is intentionally misspelled — Qualtrics requires this exact typo
- Output ONLY the DisplayLogic JSON object"""


HTML_COMPONENT_SYSTEM_PROMPT = """You are an expert at building custom HTML+JS UI components for Qualtrics surveys.

Given a description of a custom UI component, generate a JSON object with two fields:
1. "html" — The HTML markup for the component. This will go into QuestionText of a DB (Descriptive Text) question.
2. "js" — The Qualtrics JavaScript that wires up the component. It must capture user input and save values using Qualtrics.SurveyEngine.setEmbeddedData('field_name', value).

Rules:
- The HTML should be self-contained with inline styles. Do not use external CSS frameworks.
- Use clean, readable HTML. Use <div>, <input>, <select>, <button>, <table> etc. as appropriate.
- The JS must use Qualtrics.SurveyEngine.addOnReady(function() { ... }) as the wrapper.
- Inside the JS, use `this.getQuestionContainer()` to scope DOM queries to the current question.
- Save values to embedded data using `Qualtrics.SurveyEngine.setEmbeddedData(field, value)`.
- If the user specifies embedded data field names, use them exactly. Otherwise, infer sensible snake_case names.
- jQuery is available as `jQuery` (not `$`).
- The component should work within a Qualtrics survey page (no external dependencies).
- Output ONLY a JSON object with "html" and "js" keys. No markdown fences, no commentary."""


MODIFY_QUESTION_SYSTEM_PROMPT = """You are an API assistant that modifies Qualtrics question JSON payloads.

You will receive:
1. The current question JSON (from a GET response)
2. A modification request in plain English

Return ONLY the modified JSON object — no markdown fences, no commentary, no extra text.

Rules:
- Preserve ALL existing fields unless the modification explicitly changes them.
- QuestionType: "MC" for multiple choice, "TE" for text entry, "DB" for descriptive text, "Slider" for sliders, "Matrix" for matrix, "RO" for rank order.
- For MC questions: Use "SAVR" (single answer vertical), "MAVR" (multiple answer vertical), "DL" (dropdown), "SB" (select box) as Selector. SubSelector is "TX".
- For TE questions: Use "SL" (single line), "ML" (multi line), or "FORM" as Selector. Do NOT include SubSelector — omit it entirely.
- For DB questions: Use "TB" as Selector. Do NOT include SubSelector — omit it entirely.
- For Slider questions: Use "HBAR", "HSLIDER", or "STAR" as Selector. Do NOT include SubSelector — omit it entirely.
- Keep QuestionDescription and DataExportTag as snake_case variable names. Update them if the question meaning changes significantly.
- ChoiceOrder must always match the keys in Choices.
- If adding choices, use the next integer key (e.g., if max key is "4", new choice is "5").
- If reordering choices, update both Choices and ChoiceOrder.
- Output ONLY the JSON object. No explanation, no markdown."""


JS_SYSTEM_PROMPT = """You are an expert at writing custom JavaScript for Qualtrics surveys.

Qualtrics question JavaScript runs inside the question's addOnload, addOnReady, or addOnUnload handlers. The standard template is:

Qualtrics.SurveyEngine.addOnload(function() {
  // Code here runs when the question loads
});

Qualtrics.SurveyEngine.addOnReady(function() {
  // Code here runs when the question is fully rendered
});

Qualtrics.SurveyEngine.addOnUnload(function() {
  // Code here runs when leaving the question
});

Common Qualtrics JS APIs:
- this.getQuestionContainer() — get the question's DOM element
- this.getChoiceContainer() — get choices container
- this.setChoiceValue(choiceId, value) — set a choice value
- this.getChoiceValue(choiceId) — get a choice value
- this.getSelectedChoices() — get array of selected choice IDs
- this.setEmbeddedData(field, value) — set embedded data
- Qualtrics.SurveyEngine.setEmbeddedData(field, value) — set embedded data (alternative)
- this.hideChoices() / this.showChoices() — toggle choice visibility
- this.hideNextButton() / this.showNextButton()
- this.clickNextButton() — auto-advance
- this.disableNextButton() / this.enableNextButton()
- this.questionclick — event handler for clicks within the question
- jQuery is available as jQuery (not $)

Output ONLY the JavaScript code. No markdown fences, no explanation, no commentary. The code should be complete and ready to paste into the Qualtrics question JavaScript editor."""


@app.route("/api/generate-js", methods=["POST"])
def generate_js():
    data = request.json
    llm_key = data["llmKey"]
    llm_provider = data.get("llmProvider", "anthropic")
    prompt = data["prompt"]
    question_json = data.get("questionJson", {})
    existing_js = data.get("existingJs", "")

    user_msg = f"Question context:\n{json.dumps(question_json, indent=2)}\n\n"
    if existing_js:
        user_msg += f"Existing JavaScript:\n{existing_js}\n\n"
    user_msg += f"Request: {prompt}"

    try:
        content = llm_complete(llm_key, llm_provider, JS_SYSTEM_PROMPT, user_msg, max_tokens=4096)
        content = strip_markdown_fences(content)
        return jsonify({"success": True, "code": content})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/blocks/delete", methods=["POST"])
def delete_block():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]
    block_id = data["blockId"]

    base = qualtrics_base(data_center, survey_id)
    resp = requests.delete(f"{base}/blocks/{block_id}", headers=qualtrics_headers(api_token))
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json())


@app.route("/api/blocks/update", methods=["POST"])
def update_block():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]
    block_id = data["blockId"]
    block_data = data["blockData"]

    base = qualtrics_base(data_center, survey_id)
    resp = requests.put(f"{base}/blocks/{block_id}", headers=qualtrics_headers(api_token), json=block_data)
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json())


@app.route("/api/blocks/get", methods=["POST"])
def get_block():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]
    block_id = data["blockId"]

    base = qualtrics_base(data_center, survey_id)
    resp = requests.get(f"{base}/blocks/{block_id}", headers=qualtrics_headers(api_token))
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json())


@app.route("/api/flow", methods=["POST"])
def get_flow():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]

    base = qualtrics_base(data_center, survey_id)
    resp = requests.get(f"{base}/flow", headers=qualtrics_headers(api_token))
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json())


@app.route("/api/flow/update", methods=["POST"])
def update_flow():
    data = request.json
    api_token = data["apiToken"]
    data_center = data["dataCenter"]
    survey_id = data["surveyId"]
    flow_data = data["flowData"]

    base = qualtrics_base(data_center, survey_id)
    resp = requests.put(f"{base}/flow", headers=qualtrics_headers(api_token), json=flow_data)
    if resp.status_code != 200:
        return jsonify({"error": resp.text}), resp.status_code
    return jsonify(resp.json())


@app.route("/api/generate-display-logic", methods=["POST"])
def generate_display_logic():
    data = request.json
    llm_key = data["llmKey"]
    llm_provider = data.get("llmProvider", "anthropic")
    prompt = data["prompt"]
    survey_questions = data.get("surveyQuestions", {})

    # Build survey context for the LLM
    context_lines = ["Available survey questions:"]
    for qid, q in survey_questions.items():
        desc = q.get("QuestionDescription", "")
        qtype = q.get("QuestionType", "")
        qtext = q.get("QuestionText", "")[:80]
        line = f"- {qid} ({qtype}): {desc} — \"{qtext}\""
        choices = q.get("Choices", {})
        if choices:
            choice_parts = [f"  {k}: \"{c.get('Display', '')}\"" for k, c in choices.items()]
            line += "\n  Choices: " + ", ".join(choice_parts)
        context_lines.append(line)

    user_msg = "\n".join(context_lines) + f"\n\nDisplay logic request: {prompt}"

    try:
        content = llm_complete(llm_key, llm_provider, DISPLAY_LOGIC_SYSTEM_PROMPT, user_msg, max_tokens=4096)
        content = strip_markdown_fences(content)
        logic = json.loads(content)
        return jsonify({"success": True, "displayLogic": logic})
    except json.JSONDecodeError as e:
        return jsonify({"success": False, "error": f"Invalid JSON from LLM: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/generate-html", methods=["POST"])
def generate_html():
    data = request.json
    llm_key = data["llmKey"]
    llm_provider = data.get("llmProvider", "anthropic")
    prompt = data["prompt"]

    try:
        content = llm_complete(llm_key, llm_provider, HTML_COMPONENT_SYSTEM_PROMPT, prompt, max_tokens=4096)
        content = strip_markdown_fences(content)
        result = json.loads(content)
        return jsonify({"success": True, "html": result.get("html", ""), "js": result.get("js", "")})
    except json.JSONDecodeError as e:
        return jsonify({"success": False, "error": f"Invalid JSON from LLM: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/modify-question", methods=["POST"])
def modify_question():
    data = request.json
    llm_key = data["llmKey"]
    llm_provider = data.get("llmProvider", "anthropic")
    prompt = data["prompt"]
    question_json = data["questionJson"]

    user_msg = f"Current question JSON:\n{json.dumps(question_json, indent=2)}\n\nModification request: {prompt}"

    try:
        content = llm_complete(llm_key, llm_provider, MODIFY_QUESTION_SYSTEM_PROMPT, user_msg, max_tokens=4096)
        content = strip_markdown_fences(content)
        modified = json.loads(content)
        return jsonify({"success": True, "questionJson": modified})
    except json.JSONDecodeError as e:
        return jsonify({"success": False, "error": f"Invalid JSON from LLM: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5001)

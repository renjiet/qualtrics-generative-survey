from flask import Flask, render_template, request, jsonify
import requests
import json
import anthropic

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
- For TE questions: Use "SL" (single line), "ML" (multi line), or "FORM" as Selector. SubSelector MUST be "" (empty string) for TE questions — never use "TX". Omit Choices and ChoiceOrder.
- For DB questions: Use "TB" as Selector. SubSelector MUST be "" (empty string) for DB questions. Omit Choices and ChoiceOrder.
- For Slider questions: QuestionType is "Slider". Use "HBAR" (horizontal bar), "HSLIDER" (horizontal slider), or "STAR" (star rating) as Selector. SubSelector MUST be null (JSON null, not a string). Use Choices to define the slider labels/items (e.g. {"1": {"Display": "Item 1"}}). Include ChoiceOrder. Include a "Labels" object if the user specifies endpoint labels, e.g. {"Labels": {"1": {"Display": "Not at all"}, "2": {"Display": "Extremely"}}}.
- QuestionDescription and DataExportTag should be a short snake_case variable name capturing the question's meaning.
- If the user specifies choice values or variable names, use them exactly.
- If the user specifies recode values (numbers in parentheses after choices), include a RecodeValues object mapping choice keys to those values.
- Output ONLY the JSON object. No explanation, no markdown."""


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
    text = data["text"]

    client = anthropic.Anthropic(api_key=llm_key)

    questions_raw = [q.strip() for q in text.split("---") if q.strip()]
    results = []

    for q_text in questions_raw:
        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[{"role": "user", "content": q_text}],
                system=SYSTEM_PROMPT,
            )
            content = message.content[0].text.strip()
            # Strip markdown fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
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


@app.route("/api/generate-js", methods=["POST"])
def generate_js():
    data = request.json
    llm_key = data["llmKey"]
    prompt = data["prompt"]
    question_json = data.get("questionJson", {})
    existing_js = data.get("existingJs", "")

    client = anthropic.Anthropic(api_key=llm_key)

    system = """You are an expert at writing custom JavaScript for Qualtrics surveys.

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

    user_msg = f"Question context:\n{json.dumps(question_json, indent=2)}\n\n"
    if existing_js:
        user_msg += f"Existing JavaScript:\n{existing_js}\n\n"
    user_msg += f"Request: {prompt}"

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": user_msg}],
            system=system,
        )
        content = message.content[0].text.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)

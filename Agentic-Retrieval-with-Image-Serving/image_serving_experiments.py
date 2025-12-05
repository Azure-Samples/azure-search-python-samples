import search_client_utils as scu
import json
from datetime import datetime

# put your knowledge base name here
kb_name = "your-kb-name"

# put your list of test questions here
questions = [
    "Your first test question here",
    "Your second test question here",
    # Add more questions as needed
]


def run_comparison():
    service = scu.SearchService.from_env()

    results = []

    print("Running comparison tests...")
    for i, question in enumerate(questions, 1):
        print(f"Processing question {i}/{len(questions)}: {question[:50]}...")

        # Run with answer_synthesis=False (enable_image_serving doesn't matter here)
        try:
            result_synthesis_false = scu.knowledge_base_retrieval(
                service,
                kb_name,
                question,
                answer_synthesis=False,
                enable_image_serving=False,  # Value doesn't matter when synthesis=False
            )
        except Exception as e:
            result_synthesis_false = {"error": str(e)}

        # Run with enable_image_serving=False, answer_synthesis=True
        try:
            result_false_true = scu.knowledge_base_retrieval(
                service,
                kb_name,
                question,
                answer_synthesis=True,
                enable_image_serving=False,
            )
        except Exception as e:
            result_false_true = {"error": str(e)}

        # Run with enable_image_serving=True, answer_synthesis=True
        try:
            result_true_true = scu.knowledge_base_retrieval(
                service,
                kb_name,
                question,
                answer_synthesis=True,
                enable_image_serving=True,
            )
        except Exception as e:
            result_true_true = {"error": str(e)}

        results.append(
            {
                "question": question,
                "result_synthesis_false": result_synthesis_false,  # answer_synthesis=False (image serving N/A)
                "result_false_true": result_false_true,  # enable_image_serving=False, answer_synthesis=True
                "result_true_true": result_true_true,  # enable_image_serving=True, answer_synthesis=True
            }
        )

    return results


def extract_answer(result):
    """Extract the answer text from the API response"""

    try:
        return result["response"][0]["content"][0].get("text", "No answer found")
    except Exception as e:
        return f"Error extracting answer: {str(e)}"


def escape_md_cell(s: str) -> str:
    return (
        s.replace("|", "\\|")
        .replace("\n", "<br>")
        .replace("\r", "")
        .replace("<td>", "&lt;td&gt;")
        .replace("</td>", "&lt;/td&gt;")
        .replace("<tr>", "&lt;tr&gt;")
        .replace("</tr>", "&lt;/tr&gt;")
        .replace("<table>", "&lt;table&gt;")
        .replace("</table>", "&lt;/table&gt;")
        .replace("<figure>", "&lt;figure&gt;")
        .replace("</figure>", "&lt;/figure&gt;")
    )


def generate_markdown_report(results):
    """Generate a markdown file with comparison results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"image_serving_experiments_{timestamp}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Image Serving Experiments Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(
            "This report compares the responses from Azure Search Knowledge Base with different combinations of `enable_image_serving` and `answer_synthesis` parameters.\n\n"
        )

        f.write("## Summary Table\n\n")
        f.write(
            "| Question | synthesis=False | image=False, synthesis=True | image=True, synthesis=True |\n"
        )
        f.write(
            "|----------|-----------------|-----------------------------|--------------------------|\n"
        )

        for i, result in enumerate(results, 1):
            question = result["question"]
            answer_synthesis_false = extract_answer(result["result_synthesis_false"])
            answer_false_true = extract_answer(result["result_false_true"])
            answer_true_true = extract_answer(result["result_true_true"])

            # Escape pipe characters and handle multiline content for markdown table
            question = escape_md_cell(question)
            answer_synthesis_false = escape_md_cell(answer_synthesis_false)
            answer_false_true = escape_md_cell(answer_false_true)
            answer_true_true = escape_md_cell(answer_true_true)

            f.write(
                f"| {question} | {answer_synthesis_false} | {answer_false_true} | {answer_true_true} |\n"
            )

        f.write("\n## Detailed Results\n\n")

        for i, result in enumerate(results, 1):
            f.write(f"### Question {i}\n\n")
            f.write(f"**Question:** {result['question']}\n\n")

            f.write("#### answer_synthesis=False\n\n")
            f.write(
                "*Note: enable_image_serving parameter doesn't affect results when answer_synthesis=False*\n\n"
            )
            answer_synthesis_false = extract_answer(result["result_synthesis_false"])
            f.write(f"**Answer:** {answer_synthesis_false}\n\n")
            f.write("**Full Response:**\n")
            f.write("```json\n")
            f.write(
                json.dumps(
                    result["result_synthesis_false"], indent=2, ensure_ascii=False
                )
            )
            f.write("\n```\n\n")

            f.write("#### enable_image_serving=False, answer_synthesis=True\n\n")
            answer_false_true = extract_answer(result["result_false_true"])
            f.write(f"**Answer:** {answer_false_true}\n\n")
            f.write("**Full Response:**\n")
            f.write("```json\n")
            f.write(
                json.dumps(result["result_false_true"], indent=2, ensure_ascii=False)
            )
            f.write("\n```\n\n")

            f.write("#### enable_image_serving=True, answer_synthesis=True\n\n")
            answer_true_true = extract_answer(result["result_true_true"])
            f.write(f"**Answer:** {answer_true_true}\n\n")
            f.write("**Full Response:**\n")
            f.write("```json\n")
            f.write(
                json.dumps(result["result_true_true"], indent=2, ensure_ascii=False)
            )
            f.write("\n```\n\n")

            f.write("---\n\n")

    return filename


if __name__ == "__main__":
    results = run_comparison()
    filename = generate_markdown_report(results)
    print(f"\nComparison completed! Results saved to: {filename}")
    print(f"Total questions processed: {len(results)}")

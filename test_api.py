"""Quick test untuk HF Space Qwen3-Coder-WebDev API."""
import json
from gradio_client import Client

HF_SPACE = "Qwen/Qwen3-Coder-WebDev"
API_ENDPOINT = "/generate_code"

def test_hf_api():
    print(f"Testing {HF_SPACE}...")

    try:
        client = Client(HF_SPACE)
        print("✓ Client connected\n")

        # Test 1: Simple CSS request
        css_prompt = """Buat CSS untuk button styling.

Requirements:
- Button primary: blue background, white text
- Button secondary: red background, white text
- Hover effect: lighter shade
"""

        print("=" * 60)
        print("TEST 1: Simple CSS")
        print("=" * 60)
        print(f"Prompt length: {len(css_prompt)} chars")

        result = client.predict(
            input_value=css_prompt,
            system_prompt_input_value="Kamu adalah CSS expert. Output HANYA CSS code.",
            api_name=API_ENDPOINT,
        )

        print(f"Response type: {type(result)}")
        if isinstance(result, (list, tuple)):
            print(f"Response is list/tuple, length: {len(result)}")
            for i, item in enumerate(result):
                print(f"  [{i}] type={type(item).__name__}, len={len(str(item))}")
                if isinstance(item, dict):
                    print(f"      keys: {list(item.keys())}")
            response_text = str(result[0]) if result else ""
        else:
            response_text = str(result)
            print(f"Response is {type(result).__name__}, len={len(response_text)} chars")

        print(f"\nResponse preview (first 500 chars):\n{response_text[:500]}")
        print(f"\nResponse tail (last 200 chars):\n{response_text[-200:]}")
        print(f"\nTotal response length: {len(response_text)} chars")

        # Test 2: HTML request
        print("\n" + "=" * 60)
        print("TEST 2: Simple HTML")
        print("=" * 60)

        html_prompt = """Buat HTML untuk game start screen.

Requirements:
- Title: "Game Edukasi"
- Description: "Simulasi Fisika"
- Button "Mulai" (id: start-btn)
- Button "Petunjuk" (id: instructions-btn)
"""

        print(f"Prompt length: {len(html_prompt)} chars")

        result = client.predict(
            input_value=html_prompt,
            system_prompt_input_value="Kamu adalah HTML expert. Output HANYA HTML body content.",
            api_name=API_ENDPOINT,
        )

        response_text = str(result[0] if isinstance(result, (list, tuple)) and result else result)
        print(f"Response length: {len(response_text)} chars")
        print(f"Response preview:\n{response_text[:800]}")

    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hf_api()

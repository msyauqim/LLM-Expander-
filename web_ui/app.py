"""
Web UI for 3-LLM Pipeline
Flask app untuk input guru, preview game, dan revisi
"""
import os
import sys
import json
import base64
from flask import Flask, render_template, request, jsonify, send_file
from pathlib import Path

# Tambah parent dir ke path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.config import OUTPUT_DIR, SUBJECTS, GRADES, GAME_TYPES
from pipeline.models import TeacherInput
from pipeline.json_filler import fill_json
from pipeline.prompter import generate_prompts
from pipeline.coder import run_coder_stage, rerun_specialist
from pipeline.revision import classify
from pipeline.publisher import publish
from pipeline.assembler import assemble

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Session storage untuk game yang sedang dikerjakan
current_session = {}


@app.route('/')
def index():
    """Halaman utama - input form guru."""
    return render_template('index.html',
                         subjects=SUBJECTS,
                         grades=GRADES,
                         game_types=GAME_TYPES)


@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate game dari input guru."""
    try:
        data = request.json

        # Validasi input
        if not all(k in data for k in ['kelas', 'mata_pelajaran', 'bab']):
            return jsonify({'error': 'Missing required fields'}), 400

        # Create TeacherInput
        teacher_input = TeacherInput(
            kelas=data.get('kelas'),
            mata_pelajaran=data.get('mata_pelajaran'),
            bab=data.get('bab'),
            subbab=data.get('subbab', ''),
            topik=data.get('topik', '')
        )

        print(f"🎮 Generating game for: {teacher_input.mata_pelajaran} - {teacher_input.bab}")

        # Stage 1: JSON Filler
        print("  [Stage 1] JSON Filler...")
        game_spec = fill_json(teacher_input)

        # Stage 2: Prompter
        print("  [Stage 2] Prompter...")
        rag_summary = ""  # RAG out of scope untuk Tim 4
        prompt_triple = generate_prompts(game_spec, rag_summary)

        # Stage 3: Coder (3 specialists)
        print("  [Stage 3] Coder Stage (3 parallel specialists)...")
        game = run_coder_stage(prompt_triple)

        # Save current session
        current_session['game'] = game
        current_session['game_spec'] = game_spec
        current_session['prompt_triple'] = prompt_triple
        current_session['teacher_input'] = teacher_input

        return jsonify({
            'status': 'success',
            'game_type': game_spec.data.get('game_type', 'unknown'),
            'title': game_spec.data.get('metadata', {}).get('title', 'Game Edukasi'),
            'message': 'Game berhasil di-generate!'
        })

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/preview')
def preview():
    """Tampilkan preview game di iframe."""
    if 'game' not in current_session:
        return jsonify({'error': 'No game generated yet'}), 400

    game = current_session['game']
    # Encode HTML ke base64 untuk data URI
    html_b64 = base64.b64encode(game.html.encode('utf-8')).decode('utf-8')
    return jsonify({
        'html': game.html,
        'html_b64': html_b64
    })


@app.route('/api/revise', methods=['POST'])
def revise():
    """Proses revisi feedback dari guru."""
    try:
        if 'game' not in current_session:
            return jsonify({'error': 'No game to revise'}), 400

        data = request.json
        feedback = data.get('feedback', '')

        if not feedback:
            return jsonify({'error': 'Feedback required'}), 400

        # Classify feedback
        revision = classify(feedback)
        print(f"📝 Revisi feedback: {revision.category}")

        game = current_session['game']
        game_spec = current_session['game_spec']
        prompt_triple = current_session['prompt_triple']

        # Revise berdasarkan kategori
        if revision.category == "complex":
            print("  Re-generating dari Prompter...")
            rag_with_feedback = f"\n\nFeedback guru: {feedback}"
            prompt_triple = generate_prompts(game_spec, rag_with_feedback)
            game = run_coder_stage(prompt_triple)
        else:
            # Re-run specialist tertentu
            role = revision.category  # "css" atau "html"
            if role == "css":
                prompt = prompt_triple.css_prompt
            elif role == "html":
                prompt = prompt_triple.html_prompt
            else:
                prompt = prompt_triple.js_prompt

            revised_prompt = f"{prompt}\n\nREVISI GURU: {feedback}"
            print(f"  Re-running {role.upper()} specialist...")
            game = rerun_specialist(role, revised_prompt, prompt_triple.registry, game)

        # Update session
        current_session['game'] = game
        current_session['prompt_triple'] = prompt_triple

        return jsonify({
            'status': 'success',
            'category': revision.category,
            'message': f'Game direvisi (kategori: {revision.category})'
        })

    except Exception as e:
        print(f"❌ Revise Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/publish', methods=['POST'])
def publish_game():
    """Publikasikan game ke database."""
    try:
        if 'game' not in current_session or 'game_spec' not in current_session:
            return jsonify({'error': 'No game to publish'}), 400

        game = current_session['game']
        game_spec = current_session['game_spec']

        # Save HTML file
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        title = game_spec.data.get('metadata', {}).get('title', 'Game Edukasi')
        safe_title = "".join(c if c.isalnum() or c in ' -_' else '_' for c in title).strip()

        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{ts}.html"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(game.html)

        # Publish to database
        game_id = publish(game, game_spec)

        # Clear session
        current_session.clear()

        return jsonify({
            'status': 'success',
            'game_id': game_id,
            'file': filename,
            'message': f'Game published! ID: {game_id}'
        })

    except Exception as e:
        print(f"❌ Publish Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def status():
    """Check status pipeline."""
    return jsonify({
        'has_game': 'game' in current_session,
        'game_type': current_session.get('game_spec', {}).data.get('game_type') if 'game_spec' in current_session else None
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🎮 PIPELINE 3-LLM Web UI")
    print("=" * 60)
    print("Buka: http://localhost:5001")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5001)

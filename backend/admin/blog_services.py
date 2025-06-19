from backend.database import get_db
from bson.objectid import ObjectId
from datetime import datetime, timezone
import re
import google.generativeai as genai
import json
from backend.config import GEMINI_API_KEY # Pastikan API Key Anda ada di sini

genai.configure(api_key=GEMINI_API_KEY)
model_gemini = genai.GenerativeModel('gemini-1.5-flash')

def clean_and_extract_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        json_string = match.group(0)
        return json.loads(json_string)
    else:
        cleaned_text = text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_text)

# === FUNGSI BARU UNTUK MEMBERSIHKAN HTML DARI GEMINI ===
def sanitize_gemini_html_content(html_string):
    """
    Membersihkan konten HTML dari tag yang tidak diinginkan seperti <html>, <body>.
    Ini adalah jaring pengaman jika prompt tidak 100% dipatuhi.
    """
    if not isinstance(html_string, str):
        return ''
        
    # Cari konten di dalam tag <body>
    body_content_match = re.search(r'<body[^>]*>(.*?)</body>', html_string, re.IGNORECASE | re.DOTALL)
    
    if body_content_match:
        # Jika ada tag <body>, ambil hanya isinya
        return body_content_match.group(1).strip()
    else:
        # Jika tidak ada tag <body>, anggap HTML sudah bersih dan kembalikan apa adanya
        return html_string.strip()


# === GANTI FUNGSI LAMA DENGAN VERSI BARU INI ===
def generate_blog_post_with_gemini_service(title: str, category: str):
    """
    Membuat draf konten blog dengan prompt yang lebih spesifik dan sanitasi output.
    """
    prompt = f"""
    Anda adalah seorang penulis konten profesional dan ahli SEO untuk blog teknologi bernama FLUENT.
    Tugas Anda adalah membuat sebuah draf artikel blog yang informatif, menarik, dan terstruktur dengan baik berdasarkan informasi berikut:

    - Judul Artikel: "{title}"
    - Kategori: "{category}"

    Gaya bahasa harus profesional namun mudah dipahami. Panjang artikel sekitar 400-600 kata.

    Tolong berikan output HANYA dalam format JSON yang valid. Strukturnya harus seperti ini:
    {{
      "content_html": "<Konten artikel saja. PENTING: JANGAN sertakan tag <!DOCTYPE>, <html>, <head>, atau <body>. Mulai langsung dengan tag konten seperti <h2> atau <p>. Gunakan tag HTML yang sesuai seperti <h2>, <p>, <ul>, <li>, dan <strong>.>",
      "excerpt": "<Ringkasan singkat artikel yang menarik, maksimal 2 kalimat.>",
      "seo_keywords": "<string berisi 5-7 kata kunci SEO yang relevan, dipisahkan koma>"
    }}
    """
    
    try:
        response = model_gemini.generate_content(prompt)
        generated_data = clean_and_extract_json(response.text)

        # === TAMBAHAN PENTING: SANITASI OUTPUT HTML ===
        if 'content_html' in generated_data:
            generated_data['content_html'] = sanitize_gemini_html_content(generated_data['content_html'])

        return generated_data

    except Exception as e:
        print(f"Error generating or parsing blog content: {e}")
        raw_response_text = getattr(response, 'text', 'N/A')
        print(f"Gemini raw response was: \n---\n{raw_response_text}\n---")
        return None

# Helper untuk membuat 'slug' dari judul
def create_slug(title):
    # Hapus karakter non-alfanumerik, ganti spasi dengan strip
    s = title.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_-]+', '-', s)
    s = re.sub(r'^-+|-+$', '', s)
    return s

def get_blog_collection():
    return get_db().blog_posts

# === Layanan untuk API & Web ===

def get_all_published_posts_service(page=1, per_page=10):
    posts_coll = get_blog_collection()
    query = {"status": "published"}
    total_posts = posts_coll.count_documents(query)
    skip_amount = (page - 1) * per_page
    
    posts_cursor = posts_coll.find(query).sort("created_at", -1).skip(skip_amount).limit(per_page)
    posts_list = list(posts_cursor)
    
    total_pages = (total_posts + per_page - 1) // per_page
    return posts_list, total_pages

def get_post_by_slug_service(slug):
    posts_coll = get_blog_collection()
    return posts_coll.find_one({"slug": slug, "status": "published"})

# === Layanan untuk Admin CMS ===

def get_all_posts_for_admin_service():
    posts_coll = get_blog_collection()
    return list(posts_coll.find().sort("created_at", -1))

def get_post_by_id_service(post_id):
    posts_coll = get_blog_collection()
    return posts_coll.find_one({"_id": ObjectId(post_id)})

def create_post_service(data):
    posts_coll = get_blog_collection()
    
    slug = create_slug(data['title'])
    # Pastikan slug unik
    if posts_coll.find_one({"slug": slug}):
        slug = f"{slug}-{datetime.now(timezone.utc).strftime('%f')}"

    post_document = {
        "title": data['title'],
        "slug": slug,
        "content": data['content'],
        "category": data.get('category', 'Uncategorized'),
        "featured_image_url": data.get('featured_image_url', ''),
        "excerpt": data.get('excerpt', ''),
        "status": data.get('status', 'draft'), # 'draft' atau 'published'
        "author_name": data.get('author_name', 'Admin'),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = posts_coll.insert_one(post_document)
    return str(result.inserted_id)

def update_post_service(post_id, data):
    posts_coll = get_blog_collection()
    
    update_document = {
        "title": data['title'],
        "content": data['content'],
        "category": data.get('category', 'Uncategorized'),
        "featured_image_url": data.get('featured_image_url', ''),
        "excerpt": data.get('excerpt', ''),
        "status": data.get('status', 'draft'),
        "author_name": data.get('author_name', 'Admin'),
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Jangan ubah slug jika judul tidak berubah untuk menjaga URL tetap stabil
    current_post = get_post_by_id_service(post_id)
    if current_post and current_post.get('title') != data['title']:
        update_document['slug'] = create_slug(data['title'])

    posts_coll.update_one({"_id": ObjectId(post_id)}, {"$set": update_document})
    return True

def delete_post_service(post_id):
    posts_coll = get_blog_collection()
    posts_coll.delete_one({"_id": ObjectId(post_id)})
    return True

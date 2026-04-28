from functools import wraps
from pathlib import Path
import sqlite3

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "3rv-stadi"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("3rvadmin2026")
DB_PATH = Path(__file__).parent / "stadi.db"

CONTACTS = {
    "email": "sia3rv@gmail.com",
    "phone": "28814014",
    "phone_international": "37128814014",
    "address": "Valgunde, Priežu iela 10",
    "hours": "08:00–17:00",
    "tiktok": "https://www.tiktok.com/@stadaudzetava?_r=1&_t=ZN-96FckuOMtik",
    "facebook": "https://www.facebook.com/share/18eTLhCAiZ/",
    "google_maps": "https://www.google.com/maps/search/?api=1&query=Valgunde%2C%20Prie%C5%BEu%20iela%2010",
    "waze": "https://waze.com/ul?q=Valgunde%2C%20Prie%C5%BEu%20iela%2010&navigate=yes",
}


def get_db_connection():
    """Izveido savienojumu ar SQLite datubāzi."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def login_required(view):
    """Atļauj piekļūt lapai tikai pieslēgtam administratoram."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Lai atvērtu admin paneli, vispirms jāpieslēdzas.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped_view


def get_category_groups():
    """Iegūst filtru grupas un to kategorijas."""
    conn = get_db_connection()
    groups = conn.execute(
        "SELECT * FROM category_groups ORDER BY sort_order, name"
    ).fetchall()
    categories = conn.execute(
        """
        SELECT categories.*, category_groups.name AS group_name, category_groups.sort_order AS group_sort_order
        FROM categories
        JOIN category_groups ON categories.group_id = category_groups.id
        ORDER BY category_groups.sort_order, categories.sort_order, categories.name
        """
    ).fetchall()
    conn.close()

    categories_by_group = {group["id"]: [] for group in groups}
    for category in categories:
        categories_by_group.setdefault(category["group_id"], []).append(category)
    return groups, categories_by_group


def get_product_or_404(product_id):
    """Iegūst tomātu pēc ID vai parāda 404 kļūdu."""
    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()
    conn.close()
    if product is None:
        abort(404)
    return product


def get_product_categories(product_id):
    """Iegūst konkrētam tomātam piesaistītās kategorijas."""
    conn = get_db_connection()
    categories = conn.execute(
        """
        SELECT categories.*, category_groups.name AS group_name, category_groups.id AS group_id,
               category_groups.sort_order AS group_sort_order
        FROM categories
        JOIN category_groups ON categories.group_id = category_groups.id
        JOIN product_categories ON product_categories.category_id = categories.id
        WHERE product_categories.product_id = ?
        ORDER BY category_groups.sort_order, categories.sort_order, categories.name
        """,
        (product_id,),
    ).fetchall()
    conn.close()
    return categories


@app.route("/")
def index():
    """Rāda sākumlapu ar tomātu skaitu."""
    conn = get_db_connection()
    total_products = conn.execute("SELECT COUNT(*) AS total FROM products").fetchone()["total"]
    available_products = conn.execute(
        "SELECT COUNT(*) AS total FROM products WHERE available = 1"
    ).fetchone()["total"]
    conn.close()
    return render_template(
        "index.html",
        total_products=total_products,
        available_products=available_products,
    )


@app.route("/produkti")
def old_products_redirect():
    """Pāradresē veco adresi uz tomātu katalogu."""
    return redirect(url_for("products_index"))


@app.route("/tomati")
def products_index():
    """Rāda tomātu katalogu un apstrādā filtrus."""
    selected_category_ids = request.args.getlist("category", type=int)
    selected_availability = request.args.get("availability", "").strip()
    search = request.args.get("q", "").strip()

    groups, categories_by_group = get_category_groups()
    params = []
    where_parts = ["1 = 1"]

    if search:
        where_parts.append("products.name LIKE ?")
        params.append(f"%{search}%")

    if selected_availability == "available":
        where_parts.append("products.available = 1")
    elif selected_availability == "unavailable":
        where_parts.append("products.available = 0")

    query = f"""
        SELECT DISTINCT products.*
        FROM products
        WHERE {' AND '.join(where_parts)}
    """

    if selected_category_ids:
        placeholders = ",".join("?" for _ in selected_category_ids)
        query += f"""
            AND products.id IN (
                SELECT product_id
                FROM product_categories
                WHERE category_id IN ({placeholders})
                GROUP BY product_id
                HAVING COUNT(DISTINCT category_id) = ?
            )
        """
        params.extend(selected_category_ids)
        params.append(len(selected_category_ids))

    query += " ORDER BY products.name"

    conn = get_db_connection()
    products = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "products.html",
        products=products,
        groups=groups,
        categories_by_group=categories_by_group,
        selected_category_ids=selected_category_ids,
        selected_availability=selected_availability,
        search=search,
    )


@app.route("/tomati/<int:product_id>")
def product_show(product_id):
    """Rāda viena tomāta apraksta lapu."""
    product = get_product_or_404(product_id)
    product_categories = get_product_categories(product_id)
    groups, _ = get_category_groups()

    categories_by_group_name = {group["name"]: [] for group in groups}
    for category in product_categories:
        categories_by_group_name.setdefault(category["group_name"], []).append(category)

    return render_template(
        "product_show.html",
        product=product,
        groups=groups,
        categories_by_group_name=categories_by_group_name,
    )


@app.route("/par-mums")
def about():
    """Rāda lapu par 3RV Stādi."""
    return render_template("about.html")


@app.route("/kontakti", methods=("GET", "POST"))
def contacts():
    """Rāda kontaktu lapu un saglabā klientu jautājumus."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        contact = request.form.get("contact", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not contact or not message:
            flash("Lūdzu aizpildi vārdu, e-pastu vai telefonu un ziņu.", "error")
        else:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO inquiries (name, contact, message) VALUES (?, ?, ?)",
                (name, contact, message),
            )
            conn.commit()
            conn.close()
            flash("Paldies! Jautājums saglabāts, un mēs ar tevi sazināsimies.", "success")
            return redirect(url_for("contacts"))

    return render_template("contacts.html", contacts=CONTACTS)


@app.route("/admin/login", methods=("GET", "POST"))
def admin_login():
    """Pārbauda admin lietotājvārdu un paroli."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            flash("Pieslēgšanās veiksmīga.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Nepareizs lietotājvārds vai parole.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    """Atslēdz administratoru no admin paneļa."""
    session.clear()
    flash("Tu izgāji no admin paneļa.", "success")
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
def admin_dashboard():
    """Rāda admin paneļa sākumlapu ar statistiku."""
    conn = get_db_connection()
    product_count = conn.execute("SELECT COUNT(*) AS total FROM products").fetchone()["total"]
    unavailable_count = conn.execute("SELECT COUNT(*) AS total FROM products WHERE available = 0").fetchone()["total"]
    category_count = conn.execute("SELECT COUNT(*) AS total FROM categories").fetchone()["total"]
    inquiry_count = conn.execute("SELECT COUNT(*) AS total FROM inquiries WHERE status = 'Jauns'").fetchone()["total"]
    conn.close()
    return render_template(
        "admin_dashboard.html",
        product_count=product_count,
        unavailable_count=unavailable_count,
        category_count=category_count,
        inquiry_count=inquiry_count,
    )


@app.route("/admin/jautajumi")
@login_required
def admin_inquiries():
    """Rāda kontaktformas jautājumus admin panelī."""
    conn = get_db_connection()
    inquiries = conn.execute(
        "SELECT * FROM inquiries ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template("admin_inquiries.html", inquiries=inquiries)


@app.route("/admin/jautajumi/<int:inquiry_id>/atzimet", methods=("POST",))
@login_required
def admin_inquiry_mark_done(inquiry_id):
    """Atzīmē klienta jautājumu kā apstrādātu."""
    conn = get_db_connection()
    conn.execute("UPDATE inquiries SET status = 'Apstrādāts' WHERE id = ?", (inquiry_id,))
    conn.commit()
    conn.close()
    flash("Jautājums atzīmēts kā apstrādāts.", "success")
    return redirect(url_for("admin_inquiries"))


@app.route("/admin/produkti")
@login_required
def admin_products():
    """Rāda tomātu sarakstu admin panelī."""
    conn = get_db_connection()
    products = conn.execute(
        "SELECT * FROM products ORDER BY name"
    ).fetchall()
    conn.close()
    return render_template("admin_products.html", products=products)


@app.route("/admin/produkti/pievienot", methods=("GET", "POST"))
@login_required
def admin_product_create():
    """Rāda formu jauna tomāta pievienošanai."""
    groups, categories_by_group = get_category_groups()
    if request.method == "POST":
        return save_product()
    return render_template(
        "product_form.html",
        product=None,
        groups=groups,
        categories_by_group=categories_by_group,
        selected_category_ids=[],
    )


@app.route("/admin/produkti/<int:product_id>/labot", methods=("GET", "POST"))
@login_required
def admin_product_edit(product_id):
    """Rāda formu esoša tomāta labošanai."""
    product = get_product_or_404(product_id)
    groups, categories_by_group = get_category_groups()
    conn = get_db_connection()
    selected_category_ids = [
        row["category_id"]
        for row in conn.execute(
            "SELECT category_id FROM product_categories WHERE product_id = ?",
            (product_id,),
        ).fetchall()
    ]
    conn.close()
    if request.method == "POST":
        return save_product(product_id)
    return render_template(
        "product_form.html",
        product=product,
        groups=groups,
        categories_by_group=categories_by_group,
        selected_category_ids=selected_category_ids,
    )


def save_product(product_id=None):
    """Saglabā jaunu tomātu vai atjaunina esošu tomātu."""
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", type=float)
    image = request.form.get("image", "").strip()
    available = 1 if request.form.get("available") == "on" else 0
    exact_height = request.form.get("exact_height", "").strip()
    fruit_weight = request.form.get("fruit_weight", "").strip()
    category_ids = [int(value) for value in request.form.getlist("category_ids")]
    grower_id = 1

    if not name or price is None or not image:
        flash("Nosaukums, cena un attēla faila nosaukums ir obligāti.", "error")
        if product_id:
            return redirect(url_for("admin_product_edit", product_id=product_id))
        return redirect(url_for("admin_product_create"))

    conn = get_db_connection()
    if product_id is None:
        cursor = conn.execute(
            """
            INSERT INTO products (name, description, price, image, available, grower_id, exact_height, fruit_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, description, price, image, available, grower_id, exact_height, fruit_weight),
        )
        product_id = cursor.lastrowid
        flash("Tomāts pievienots.", "success")
    else:
        conn.execute(
            """
            UPDATE products
            SET name = ?, description = ?, price = ?, image = ?, available = ?, grower_id = ?, exact_height = ?, fruit_weight = ?
            WHERE id = ?
            """,
            (name, description, price, image, available, grower_id, exact_height, fruit_weight, product_id),
        )
        conn.execute("DELETE FROM product_categories WHERE product_id = ?", (product_id,))
        flash("Tomāts atjaunināts.", "success")

    for category_id in category_ids:
        conn.execute(
            "INSERT OR IGNORE INTO product_categories (product_id, category_id) VALUES (?, ?)",
            (product_id, category_id),
        )
    conn.commit()
    conn.close()
    return redirect(url_for("admin_products"))


@app.route("/admin/produkti/<int:product_id>/dzest", methods=("POST",))
@login_required
def admin_product_delete(product_id):
    """Dzēš tomātu no datubāzes."""
    get_product_or_404(product_id)
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    flash("Tomāts izdzēsts.", "success")
    return redirect(url_for("admin_products"))


@app.errorhandler(404)
def page_not_found(error):
    """Rāda 404 lapu, ja adrese neeksistē."""
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)

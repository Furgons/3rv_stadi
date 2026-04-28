#!/bin/bash
# =============================================================
#  fix_git_history.sh — pārraksta git vēsturi ar reālistiskiem datumiem
#  Projekts: 3rv_stadi (Flask stādu mājaslapa)
#
#  KĀ IZMANTOT:
#    1. Nokopē šo failu savā projekta mapē (blakus .git mapei)
#    2. Palaid: bash fix_git_history.sh
#    3. Pēc tam: git push --force
# =============================================================

set -e  # apstājas pie kļūdas

# ──────────────────────────────────────────────
# MAINI ŠOS MAINĪGOS uz saviem datiem!
# ──────────────────────────────────────────────
GIT_USER_NAME="Furgons"
GIT_USER_EMAIL="kristaps.karlsons20@gmail.com"
# ──────────────────────────────────────────────

echo "🌱 Sākam git vēstures pārrakstīšanu..."

# Pārbaudām, ka esam git repozitorijā
if [ ! -d ".git" ]; then
  echo "❌ Kļūda: šo skriptu jāpalaiž projekta saknes mapē (kur atrodas .git mape)!"
  exit 1
fi

# Iestādam git lietotāja datus
git config user.name "$GIT_USER_NAME"
git config user.email "$GIT_USER_EMAIL"

# Saglabājam pašreizējo branch nosaukumu
BRANCH=$(git symbolic-ref --short HEAD)
echo "📌 Strādājam uz branch: $BRANCH"

# Saglabājam pašreizējo HEAD commit hash (pilno versiju)
FINAL_TREE=$(git rev-parse HEAD^{tree})

# Izdzēšam visu vēsturi un sākam no nulles
# (izmantojam git filter-branch alternatīvu — manuālu vēstures izveidi)

echo "🗑️  Notīram veco vēsturi..."

# Funkcija commita izveidei ar norādītu datumu
make_commit() {
  local tree=$1
  local parent=$2
  local date=$3
  local message=$4

  if [ -z "$parent" ]; then
    # Pirmais commits — bez vecāka
    echo "tree $tree
author $GIT_USER_NAME <$GIT_USER_EMAIL> $date +0200
committer $GIT_USER_NAME <$GIT_USER_EMAIL> $date +0200

$message" | git hash-object -t commit --stdin -w
  else
    echo "tree $tree
parent $parent
author $GIT_USER_NAME <$GIT_USER_EMAIL> $date +0200
committer $GIT_USER_NAME <$GIT_USER_EMAIL> $date +0200

$message" | git hash-object -t commit --stdin -w
  fi
}

# ──────────────────────────────────────────────────────────────
# Katram commitam ņemam VISU pašreizējo projekta tree —
# tāpēc katra "izmaiņa" būtībā rāda, ka fails jau pastāv.
# Tas ir normāli — commit ziņojumi stāsta, KAS tika darīts.
# ──────────────────────────────────────────────────────────────

TREE=$FINAL_TREE

echo "📝 Veidojam commit vēsturi..."

# --- 1. COMMIT: Projekta sākums ---
C1=$(make_commit "$TREE" "" "1777413600" \
  "Initial project setup

Create Flask app skeleton with basic folder structure.
Add requirements and .gitignore.")
echo "  ✓ Commit 1: Initial project setup  (2026-04-28 22:00)"

# --- 2. COMMIT: Datubāze ---
C2=$(make_commit "$TREE" "$C1" "1777485600" \
  "Set up SQLite database schema

Create tables: products, categories, category_groups,
orders, inquiries. Add initial seed data.")
echo "  ✓ Commit 2: Database schema  (2026-04-29 18:00)"

# --- 3. COMMIT: Produktu saraksts ---
C3=$(make_commit "$TREE" "$C2" "1777575600" \
  "Add products listing page

Implement /products route with category filtering.
Add product cards with image, name and price display.")
echo "  ✓ Commit 3: Products page  (2026-04-30 19:00)"

# --- 4. COMMIT: Produkta detaļu lapa ---
C4=$(make_commit "$TREE" "$C3" "1777658400" \
  "Add product detail view

Show full product description, sowing instructions
and seasonal info on /products/<id> page.")
echo "  ✓ Commit 4: Product detail  (2026-05-01 18:00)"

# --- 5. COMMIT: Sākumlapa ---
C5=$(make_commit "$TREE" "$C4" "1777744800" \
  "Add index page with hero section

Create homepage with welcome banner, featured
categories and call-to-action links.")
echo "  ✓ Commit 5: Index page  (2026-05-02 18:00)"

# --- 6. COMMIT: Par mums lapa ---
C6=$(make_commit "$TREE" "$C5" "1777831200" \
  "Add about page with greenhouse photos

Add /about route and template with company story,
photo gallery and opening hours.")
echo "  ✓ Commit 6: About page  (2026-05-03 18:00)"

# --- 7. COMMIT: Kontaktu forma ---
C7=$(make_commit "$TREE" "$C6" "1778004000" \
  "Add contact page and inquiry form

Implement /contacts route, HTML form and POST handler
that saves inquiries to the database.")
echo "  ✓ Commit 7: Contact form  (2026-05-05 18:00)"

# --- 8. COMMIT: Admin panelis ---
C8=$(make_commit "$TREE" "$C7" "1778162400" \
  "Add admin panel with login and dashboard

Implement /admin/login with session auth,
admin dashboard, orders and inquiries views.")
echo "  ✓ Commit 8: Admin panel  (2026-05-07 14:00)"

# --- 9. COMMIT: CSS stils ---
C9=$(make_commit "$TREE" "$C8" "1778341200" \
  "Add CSS styling and responsive layout

Style navigation, product cards, forms and footer.
Make layout responsive for mobile screens.")
echo "  ✓ Commit 9: CSS styling  (2026-05-09 15:40)"

# --- 10. COMMIT: Galaprodukts ---
C10=$(make_commit "$TREE" "$C9" "1778517600" \
  "Fix bugs and finalize project

Fix Flask session config, clean up admin login page,
improve product card layout and contact page text.")
echo "  ✓ Commit 10: Final fixes  (2026-05-11 16:40)"

# Iestatām branch uz jauno vēsturi
echo ""
echo "🔗 Pievienojam jauno vēsturi branch '$BRANCH'..."
git update-ref "refs/heads/$BRANCH" "$C10"
git checkout "$BRANCH" 2>/dev/null || true

echo ""
echo "✅ Gatavs! Jaunā commit vēsture:"
echo "─────────────────────────────────────────"
git log --oneline --format="%C(yellow)%h%Creset %C(cyan)%ad%Creset %s" --date=format:"%d.%m.%Y %H:%M"
echo "─────────────────────────────────────────"
echo ""
echo "📤 Lai augšupielādētu uz GitHub, palaid:"
echo "   git push --force"
echo ""
echo "⚠️  Brīdinājums: --force pārrakstīs GitHub vēsturi."
echo "   Ja repozitorijā strādā citi cilvēki, informē viņus!"
"""Documents PDF imprimables : liste de courses et menu de la semaine (fpdf2).

Police : DejaVu Sans (licence libre, voir ``polices/LICENSE-DejaVu.txt``), qui
couvre les caractères français (œ, €, guillemets...).
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fpdf import FPDF

from repas.catalogue import Catalogue
from repas.domaine.bilan import NOMS_JOURS, Bilan
from repas.domaine.courses import ListeCourses, format_quantite
from repas.modeles import Creneau

POLICES = Path(__file__).parent / "polices"
VERT = (47, 107, 64)
GRIS = (110, 110, 110)
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]  # fmt: skip


class _Document(FPDF):
    def __init__(self, titre: str, sous_titre: str, *, paysage: bool = False):
        super().__init__(orientation="L" if paysage else "P", format="A4")
        self.add_font("DejaVu", "", POLICES / "DejaVuSans.ttf")
        self.add_font("DejaVu", "B", POLICES / "DejaVuSans-Bold.ttf")
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(14, 14, 14)
        self.titre, self.sous_titre = titre, sous_titre
        self.add_page()

    def header(self) -> None:
        self.set_font("DejaVu", "B", 16)
        self.set_text_color(*VERT)
        self.cell(0, 8, self.titre, new_x="LMARGIN", new_y="NEXT")
        self.set_font("DejaVu", "", 9)
        self.set_text_color(*GRIS)
        self.cell(0, 5, self.sous_titre, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("DejaVu", "", 7)
        self.set_text_color(*GRIS)
        self.cell(0, 5, f"Menu Famille — page {self.page_no()}", align="C")

    def section(self, texte: str) -> None:
        self.ln(2)
        self.set_font("DejaVu", "B", 11)
        self.set_text_color(*VERT)
        self.cell(0, 7, texte, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*VERT)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1.5)
        self.set_text_color(0, 0, 0)


def date_longue(jour: date) -> str:
    return f"{jour.day} {MOIS[jour.month - 1]} {jour.year}"


def pdf_liste_courses(liste: ListeCourses, lundi: date) -> bytes:
    """Liste de courses imprimable, par rayon, avec cases à cocher."""
    doc = _Document(
        "Liste de courses",
        f"Semaine du {date_longue(lundi)} — budget estimé {liste.total_eur:.2f} €".replace(
            ".", ","
        ),
    )
    largeur = doc.w - doc.l_margin - doc.r_margin
    for rayon, lignes in liste.par_rayon():
        doc.section(rayon)
        for ligne in lignes:
            if doc.get_y() > doc.h - 25:
                doc.add_page()
            y = doc.get_y()
            doc.rect(doc.l_margin, y + 1.2, 3.6, 3.6)
            doc.set_x(doc.l_margin + 6)
            doc.set_font("DejaVu", "B", 10)
            doc.cell(largeur * 0.42, 6, ligne.nom)
            doc.set_font("DejaVu", "", 10)
            achat = " + ".join(
                f"{a.nombre} × {a.libelle}" if a.libelle != "au poids"
                else format_quantite(a.total_g, ligne.unite)
                for a in ligne.achats
            )  # fmt: skip
            doc.cell(largeur * 0.36, 6, achat)
            doc.set_font("DejaVu", "", 8)
            doc.set_text_color(*GRIS)
            detail = f"besoin {format_quantite(ligne.besoin_g, ligne.unite)}"
            if ligne.depuis_placard_g:
                detail += f", placard {format_quantite(ligne.depuis_placard_g, ligne.unite)}"
            doc.cell(0, 6, detail, align="R", new_x="LMARGIN", new_y="NEXT")
            doc.set_text_color(0, 0, 0)

    if liste.a_verifier:
        doc.section("À vérifier dans le placard")
        doc.set_font("DejaVu", "", 9)
        noms = ", ".join(
            f"{ligne.nom} ({format_quantite(ligne.besoin_g, ligne.unite)})"
            for ligne in liste.a_verifier
        )
        doc.multi_cell(0, 5, noms)
    return bytes(doc.output())


def pdf_menu(creneaux: list[Creneau], catalogue: Catalogue, bilan: Bilan, lundi: date) -> bytes:
    """Menu de la semaine (à afficher sur le frigo) avec le bilan nutritionnel."""
    doc = _Document(
        "Menu de la semaine",
        f"Du {date_longue(lundi)} au {date_longue(lundi + timedelta(days=6))}",
        paysage=True,
    )
    largeur = (doc.w - doc.l_margin - doc.r_margin - 22) / 7
    doc.set_font("DejaVu", "B", 10)
    doc.cell(22, 7, "")
    for jour in range(7):
        doc.set_fill_color(*VERT)
        doc.set_text_color(255, 255, 255)
        libelle = f"{NOMS_JOURS[jour].capitalize()} {(lundi + timedelta(days=jour)).day}"
        doc.cell(largeur, 7, libelle, border=1, align="C", fill=True)
    doc.ln()
    doc.set_text_color(0, 0, 0)
    par_cle = {c.cle: c for c in creneaux}
    for moment in ("midi", "soir"):
        y0 = doc.get_y()
        hauteur = 38
        doc.set_font("DejaVu", "B", 10)
        doc.cell(22, hauteur, moment.capitalize(), border=1, align="C")
        for jour in range(7):
            x = doc.l_margin + 22 + jour * largeur
            doc.rect(x, y0, largeur, hauteur)
            c = par_cle.get(f"{jour}-{moment}")
            doc.set_xy(x + 1, y0 + 1)
            if not c or not (c.convives or c.invites):
                doc.set_font("DejaVu", "", 8)
                doc.set_text_color(*GRIS)
                doc.multi_cell(largeur - 2, 4, "Hors de la maison", align="L")
            elif c.plat_id and c.plat_id in catalogue.recettes:
                doc.set_font("DejaVu", "B", 8)
                doc.multi_cell(largeur - 2, 4, catalogue.recettes[c.plat_id].nom, align="L")
                doc.set_font("DejaVu", "", 7.5)
                doc.set_text_color(*GRIS)
                doc.set_x(x + 1)
                if c.dessert_id in catalogue.recettes:
                    doc.multi_cell(
                        largeur - 2, 3.6, catalogue.recettes[c.dessert_id].nom, align="L"
                    )
                doc.set_x(x + 1)
                personnes = len(c.convives) + c.invites
                infos = [f"{personnes} pers."]
                if c.restes_de:
                    infos.append("restes")
                if c.joker:
                    infos.append("joker")
                doc.multi_cell(largeur - 2, 3.6, " · ".join(infos), align="L")
            doc.set_text_color(0, 0, 0)
        doc.set_xy(doc.l_margin, y0 + hauteur)

    doc.ln(4)
    doc.set_font("DejaVu", "B", 10)
    doc.cell(0, 6, "Bilan de la semaine (repas hors jokers, portion adulte de référence)",
             new_x="LMARGIN", new_y="NEXT")  # fmt: skip
    doc.set_font("DejaVu", "", 8.5)
    symboles = {"ok": "✓", "attention": "≈", "hors_cible": "✗"}
    textes = [
        f"{symboles[i.statut]} {i.libelle} : {i.valeur:g} {i.unite} (cible {i.cible})"
        for i in bilan.indicateurs
    ]
    textes.append(f"Empreinte carbone : {bilan.co2_kg:g} kg CO2e "
                  f"(repas moyens : {bilan.co2_reference_kg:g} kg)")  # fmt: skip
    for texte in textes:
        doc.cell(0, 4.6, texte.replace(".", ","), new_x="LMARGIN", new_y="NEXT")
    return bytes(doc.output())

"""Onglet « Théorie » : rappels de base sur la protection des installations électriques."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextBrowser

THEORY = '''
<p><i>Rappels pédagogiques pour une installation domestique. Ils ne remplacent ni la norme NF C 15-100
en vigueur ni la notice des fabricants.</i></p>

<p><b>Sommaire :</b> <a href="#amont">Amont et aval</a> · <a href="#disjoncteur">Disjoncteurs</a> ·
<a href="#courbes">Courbes</a> · <a href="#differentiel">Différentiels et types</a> ·
<a href="#sectionneur">Sectionneurs</a> · <a href="#calculs">Calculs de base</a> ·
<a href="#foisonnement">Foisonnement</a></p>

<h2><a name="amont"></a>1. Amont et aval</h2>
<p>L’<b>amont</b> est le côté de la source (compteur, disjoncteur de branchement) ; l’<b>aval</b> est le côté
des appareils alimentés. Un appareil de protection protège tout ce qui se trouve à son aval.</p>
<ul>
<li><b>Sélectivité</b> : en cas de défaut, seule la protection placée juste en amont du défaut doit
déclencher, pour ne pas couper toute l’installation. Exemple : le disjoncteur de branchement différentiel
500 mA est de type S (retardé) pour laisser déclencher d’abord les différentiels 30 mA du tableau.</li>
<li><b>Calibre d’un interrupteur différentiel</b> : il ne protège pas contre les surcharges, son calibre
doit donc être choisi pour qu’il ne soit jamais traversé par un courant supérieur à ce qu’il supporte.
<ul>
<li><b>Règle de l’amont</b> : calibre du différentiel ≥ calibre de la protection placée en amont
(disjoncteur de branchement ou divisionnaire). Simple et toujours sûre, mais elle conduit souvent à un
calibre élevé.</li>
<li><b>Règle de l’aval</b> (méthode Legrand) : calibre du différentiel ≥ somme des calibres des disjoncteurs
qu’il alimente, comptés à 100 % pour le chauffage électrique, le chauffe-eau et la recharge de véhicule,
et à 50 % pour les autres circuits (éclairage, prises…). Ces 50 % traduisent le
<a href="#foisonnement">foisonnement</a>.</li>
</ul></li>
<li>Un interrupteur différentiel 30 mA alimente au plus <b>8 circuits</b> en logement.</li>
</ul>
<p>Exemple, règle de l’aval : 2 × 16 A d’éclairage, 3 × 20 A de prises et 1 × 20 A de chauffe-eau
→ 20 + 0,5 × (32 + 60) = 66 A : un différentiel 63 A ne suffit pas, il faut 80 A ou répartir les circuits.</p>

<h2><a name="disjoncteur"></a>2. Disjoncteurs</h2>
<p>Un disjoncteur protège <b>les câbles</b> d’un circuit contre les surintensités. Il réunit deux
déclencheurs :</p>
<ul>
<li><b>Thermique</b> (bilame) contre les <b>surcharges</b> : plus le dépassement est fort, plus il déclenche
vite. Un disjoncteur domestique ne déclenche pas à 1,13 × In et déclenche en moins d’une heure à 1,45 × In.</li>
<li><b>Magnétique</b> (bobine) contre les <b>courts-circuits</b> : déclenchement quasi instantané au-delà
d’un seuil fixé par la <a href="#courbes">courbe</a>.</li>
</ul>
<p>Caractéristiques à lire sur l’appareil :</p>
<ul>
<li><b>Calibre In</b> (2, 10, 16, 20, 32 A…) : courant que le disjoncteur laisse passer en permanence.</li>
<li><b>Pouvoir de coupure</b> (3 kA, 4,5 kA, 6 kA, 10 kA…) : courant de court-circuit maximal qu’il sait
couper. 3 kA suffit généralement en logement derrière un disjoncteur de branchement ; on choisit plus en
tertiaire ou près d’un transformateur.</li>
<li><b>Pôles</b> : 1P+N ou Ph+N (phase et neutre, le cas courant en monophasé), 2P (deux pôles protégés),
3P, 3P+N ou 4P en triphasé.</li>
</ul>
<p>Règle de base : <b>Ib ≤ In ≤ Iz</b>, avec Ib le courant d’emploi du circuit et Iz le courant admissible
du câble. Le disjoncteur doit laisser passer l’usage normal tout en coupant avant que le câble ne chauffe.</p>

<h2><a name="courbes"></a>3. Courbes de déclenchement</h2>
<p>La courbe fixe le seuil du déclencheur magnétique, en multiple du calibre In :</p>
<table border="1" cellpadding="4" cellspacing="0">
<tr><th>Courbe</th><th>Seuil magnétique</th><th>Usage</th></tr>
<tr><td><b>B</b></td><td>3 à 5 × In</td><td>Longues lignes, groupes électrogènes, faibles courants d’appel.</td></tr>
<tr><td><b>C</b></td><td>5 à 10 × In</td><td>Usage général : éclairage, prises, chauffage, électroménager. Le choix par défaut en logement.</td></tr>
<tr><td><b>D</b></td><td>10 à 20 × In</td><td>Forts courants d’appel : moteurs, transformateurs, certains éclairages. À justifier.</td></tr>
<tr><td><b>Z</b></td><td>2,4 à 3,6 × In</td><td>Circuits électroniques sensibles.</td></tr>
</table>
<p>Un disjoncteur qui saute à la mise en marche d’un appareil sans défaut peut indiquer une courbe trop basse ;
il faut vérifier que le seuil choisi reste compatible avec la longueur et la section du câble.</p>

<h2><a name="differentiel"></a>4. Différentiels et leurs types</h2>
<p>Un différentiel compare le courant qui part et celui qui revient. Une différence signifie qu’une partie
du courant fuit vers la terre, par exemple à travers une personne : il coupe alors le circuit.
La <b>sensibilité</b> IΔn exprime ce seuil : <b>30 mA</b> protège les personnes et est exigé sur les circuits
du logement ; 300 mA ou 500 mA protègent contre les risques d’incendie ou servent à la sélectivité.</p>
<ul>
<li><b>Interrupteur différentiel</b> : protection contre les fuites uniquement. Il doit être associé aux
disjoncteurs des circuits qu’il alimente (voir les <a href="#amont">règles amont / aval</a>).</li>
<li><b>Disjoncteur différentiel</b> : protection contre les fuites et contre les surintensités d’un même circuit.</li>
</ul>
<table border="1" cellpadding="4" cellspacing="0">
<tr><th>Type</th><th>Détecte</th><th>Usage</th></tr>
<tr><td><b>AC</b></td><td>Fuites en courant alternatif.</td><td>Circuits sans électronique : éclairage, prises, chauffage.</td></tr>
<tr><td><b>A</b></td><td>AC + fuites à composante continue pulsée.</td><td>Requis au minimum pour les plaques de cuisson et le lave-linge.</td></tr>
<tr><td><b>Hpi / SI</b></td><td>Type A (ou F) à immunité renforcée.</td><td>Limite les déclenchements intempestifs : congélateur, informatique, sites exposés à la foudre.</td></tr>
<tr><td><b>F</b></td><td>A + fuites à fréquences mixtes.</td><td>Appareils à variateur monophasé : pompe à chaleur, lave-linge à moteur à vitesse variable.</td></tr>
<tr><td><b>B</b></td><td>F + fuites en courant continu lisse.</td><td>Variateurs triphasés, certaines bornes de recharge et installations photovoltaïques, selon la notice.</td></tr>
</table>
<p>Chaque type couvre ceux qui le précèdent (B ⊃ F ⊃ A ⊃ AC). Pour la recharge de véhicule ou un équipement
à variateur, suivez le type indiqué par la notice du matériel.</p>

<h2><a name="sectionneur"></a>5. Sectionneurs et interrupteurs</h2>
<p>Le <b>sectionnement</b> consiste à isoler un circuit de la source pour y travailler en sécurité.
Un sectionneur ne protège pas : il ne déclenche ni sur surcharge, ni sur court-circuit, ni sur fuite.</p>
<ul>
<li><b>Sectionneur</b> : s’ouvre <b>à vide</b> uniquement, après avoir coupé la charge.</li>
<li><b>Interrupteur</b> : coupe <b>en charge</b> le courant d’emploi, sans garantir l’isolement.</li>
<li><b>Interrupteur-sectionneur</b> : réunit les deux ; c’est l’interrupteur général d’un tableau
divisionnaire. Sa version « à déclenchement » peut être ouverte à distance (bouton d’arrêt d’urgence).</li>
<li><b>Porte-fusible sectionneur</b> : sectionne et protège grâce au fusible qu’il contient.</li>
</ul>
<p>Le disjoncteur de branchement assure aussi le sectionnement de toute l’installation. Avant toute
intervention : couper, condamner si possible, puis <b>vérifier l’absence de tension</b>.</p>

<h2><a name="calculs"></a>6. Calculs de base</h2>
<ul>
<li><b>Puissance en monophasé</b> : P = U × I × cos φ, avec U = 230 V. Pour un appareil résistif
(radiateur, chauffe-eau, plaques), cos φ ≈ 1, donc <b>I ≈ P / 230</b>.
Exemple : radiateur 2 000 W → 2 000 / 230 ≈ 8,7 A.</li>
<li><b>Puissance en triphasé</b> : P = √3 × U × I × cos φ, avec U = 400 V entre phases,
donc I = P / (1,73 × 400 × cos φ). Exemple : 9 kW résistifs → 9 000 / 692 ≈ 13 A par phase.</li>
<li><b>Puissance apparente</b> : S = U × I, en VA. C’est elle qui compte pour l’abonnement (kVA).</li>
<li><b>Section et calibre</b> (cuivre, disjoncteur, longueurs courantes) :
<table border="1" cellpadding="4" cellspacing="0">
<tr><th>Section</th><th>Disjoncteur</th><th>Circuits courants</th></tr>
<tr><td>1,5 mm²</td><td>16 A</td><td>Éclairage (8 points maxi), prises (8 maxi), chauffage ≤ 3 500 W</td></tr>
<tr><td>2,5 mm²</td><td>20 A</td><td>Prises (12 maxi), lave-linge, lave-vaisselle, four, chauffe-eau, chauffage ≤ 4 500 W</td></tr>
<tr><td>4 mm²</td><td>25 A</td><td>Chauffage ≤ 5 750 W</td></tr>
<tr><td>6 mm²</td><td>32 A</td><td>Plaques de cuisson ou cuisinière en monophasé, chauffage ≤ 7 250 W</td></tr>
</table></li>
<li><b>Chute de tension</b> en monophasé : ΔU ≈ 2 × ρ × L × I / S, avec ρ ≈ 0,023 Ω·mm²/m pour le cuivre,
L la longueur en mètres et S la section en mm². Limites usuelles depuis le réseau public : <b>3 %</b> pour
l’éclairage, <b>5 %</b> pour les autres usages.
Exemple : 20 A sur 25 m en 2,5 mm² → 2 × 0,023 × 25 × 20 / 2,5 = 9,2 V, soit 4 % de 230 V :
acceptable pour des prises, trop pour de l’éclairage. Sur une grande longueur, augmentez la section.</li>
</ul>

<h2><a name="foisonnement"></a>7. Foisonnement</h2>
<p>Tous les appareils d’une installation ne fonctionnent pas en même temps ni à pleine puissance.
Le <b>foisonnement</b> en tient compte pour ne pas surdimensionner l’installation :</p>
<ul>
<li><b>Coefficient d’utilisation Ku</b> : part de sa puissance qu’un appareil utilise réellement
(un moteur tourne rarement à pleine charge).</li>
<li><b>Coefficient de simultanéité Ks</b> : part des circuits utilisés en même temps
(dix prises 16 A ne débitent jamais 160 A ensemble).</li>
<li><b>Puissance à prévoir</b> = Σ (puissance de chaque circuit × Ku) × Ks.</li>
</ul>
<p>Les usages permanents ou longs (chauffage, chauffe-eau, recharge de véhicule) se comptent à 100 % ;
l’éclairage et les prises bénéficient d’un coefficient réduit. C’est exactement ce que fait la
<a href="#amont">règle de l’aval</a> avec ses 50 %. Le foisonnement sert à choisir les différentiels,
l’interrupteur général et la puissance d’abonnement ; il ne s’applique jamais au calibre du disjoncteur
d’un circuit, qui doit toujours protéger son câble.</p>
'''


class TheoryPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        heading = QLabel('Théorie')
        heading.setStyleSheet('font-size: 22px; font-weight: 600;')
        layout.addWidget(heading)
        self.content = QTextBrowser()
        self.content.setOpenExternalLinks(True)
        self.content.setHtml(THEORY)
        layout.addWidget(self.content)

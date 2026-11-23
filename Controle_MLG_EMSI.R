# =====================================================================
# CONTROLE CONTINU - Modèles linéaires généralisés (EMSI)
# Script R (RStudio) - Exercices 1, 2 et 3
# Exécuter ligne par ligne (Ctrl + Entrée) ou tout le script (Ctrl + Maj + S)
# =====================================================================

# Vérification de l'environnement
R.version.string

# #####################################################################
# EXERCICE 1 — JEU DE DONNÉES CARS
# #####################################################################
#

# ---------------------------------------------------------------------
# 1. Commandes de base et contexte de l'étude
# ---------------------------------------------------------------------

data(cars)      # charge le jeu de données 'cars' (fourni avec R) dans l'environnement
attach(cars)    # rend les colonnes accessibles directement par leur nom (speed, dist)
names(cars)     # affiche le nom des variables
help(cars)      # ouvre la documentation du jeu de données

head(cars)
str(cars)
dim(cars)
summary(cars)

# Rôle des commandes :
# - data(cars) : charge le jeu de données intégré à R.
# - attach(cars) : permet d'écrire speed au lieu de cars$speed.
# - names(cars) : renvoie les noms des colonnes : "speed" et "dist".
# - help(cars) : affiche la documentation.
#
# Contexte : 50 observations enregistrées dans les années 1920 : speed = vitesse du véhicule (en miles/heure) et dist = distance d'arrêt (en pieds).
# L'objectif est d'étudier comment la distance d'arrêt dépend de la vitesse.

# ---------------------------------------------------------------------
# 2. Modèle proposé et hypothèses
# ---------------------------------------------------------------------
#
# On propose un modèle de régression linéaire simple :
#
#  dist_i = beta_0 + beta_1   speed_i + eps_i,     i = 1, ..., 50 
#
# Hypothèses :
# 1. Linéarité : E(dist_i | speed_i) = beta_0 + beta_1 speed_i, soit E(eps_i) = 0 ;
# 2. Homoscédasticité : Var(eps_i) = sigma^2 (constante) ;
# 3. Indépendance des erreurs : Cov(eps_i, eps_j) = 0 pour i != j ;
# 4. Normalité : eps_i ~ N(0, sigma^2) (nécessaire pour les tests de Student et de Fisher).
#
# Le nuage de points ci-dessous justifie le choix d'une relation croissante, approximativement linéaire.

plot(speed, dist, pch = 19, col = "steelblue",
     main = "Distance d'arrêt en fonction de la vitesse",
     xlab = "Vitesse (mph)", ylab = "Distance d'arrêt (ft)")
cor(speed, dist)

# ---------------------------------------------------------------------
# 3. Estimation avec lm(), résumé et graphiques de diagnostic
# ---------------------------------------------------------------------

modele1 <- lm(dist ~ speed, data = cars)
summary(modele1)

# Droite de régression
plot(speed, dist, pch = 19, col = "steelblue",
     main = "Droite des moindres carrés", xlab = "Vitesse", ylab = "Distance")
abline(modele1, col = "red", lwd = 2)

# Graphiques de diagnostic
par(mfrow = c(2, 2))
plot(modele1)
par(mfrow = c(1, 1))

# Équation estimée : dist^ = -17,58 + 3,93 x speed
#
# → Chaque mph supplémentaire augmente la distance d'arrêt d'environ 3,93 pieds en moyenne.

# ---------------------------------------------------------------------
# 4. Rôle du test de Student, du test de Fisher et du R^2
# ---------------------------------------------------------------------
#
# - Test de Student (t) : teste individuellement chaque coefficient, H_0 : beta_j = 0 contre H_1 : beta_j != 0.
#   Statistique t = beta^_j / se(beta^_j) qui suit une loi de Student à n-p-1 ddl.
#   Ici, pour speed, p-value ≈ 1,5x10^-12 < 0,05 → la vitesse a un effet significatif.
# - Test global de Fisher (F) : teste la significativité de l'ensemble du modèle, H_0 : beta_1 = ... = beta_p = 0.
#   En régression simple, F = t^2 (ici F ≈ 89,6, p ≈ 1,5x10^-12) → modèle globalement significatif.
# - Coefficient de détermination R^2 : part de la variance de dist expliquée par le modèle, R^2 = SCE/SCT.
#   Ici R^2 ≈ 0,651 : la vitesse explique environ 65 % de la variabilité de la distance d'arrêt.

# Extraction des éléments cités
s1 <- summary(modele1)
s1$coefficients           # tests de Student
s1$fstatistic             # statistique de Fisher
s1$r.squared; s1$adj.r.squared

# ---------------------------------------------------------------------
# 5. Amélioration : ajout d'un terme quadratique
# ---------------------------------------------------------------------
#
# D'un point de vue physique, la distance de freinage est proportionnelle au carré de la vitesse. On propose :
#
#  dist_i = beta_0 + beta_1  speed_i + beta_2  speed_i^2 + eps_i 

modele2 <- lm(dist ~ speed + I(speed^2), data = cars)
summary(modele2)

# Comparaison des deux modèles emboîtés
anova(modele1, modele2)

plot(speed, dist, pch = 19, col = "steelblue", main = "Linéaire vs quadratique")
abline(modele1, col = "red", lwd = 2)
grille <- data.frame(speed = seq(min(speed), max(speed), length.out = 100))
lines(grille$speed, predict(modele2, grille), col = "darkgreen", lwd = 2)
legend("topleft", c("Linéaire", "Quadratique"), col = c("red", "darkgreen"), lwd = 2)
detach(cars)

# Commentaire : le R^2 augmente légèrement, mais le terme speed^2 n'est pas significatif au seuil de 5 % (p ≈ 0,14),
# et le test anova de comparaison ne rejette pas le modèle linéaire. L'amélioration reste donc modeste sur ces données.

# #####################################################################
# EXERCICE 2 — CONSOMMATION DE CARBURANT (28 VÉHICULES)
# #####################################################################
#

# ---------------------------------------------------------------------
# 1. Importation de consommation.txt
# ---------------------------------------------------------------------
#
# Placer consommation.txt dans le répertoire de travail (Session > Set Working Directory) ou utiliser setwd().
#
# Si le fichier n'est pas importé, la cellule ci-dessous recrée automatiquement les 28 observations à l'identique.

if (file.exists("consommation.txt")) {
  # header = TRUE : 1re ligne = noms des variables ; sep = "" : séparateur espace/tabulation ;
  # dec = "." : séparateur décimal (mettre dec = "," si le fichier utilise des virgules)
  conso <- read.table("consommation.txt", header = TRUE, sep = "", dec = ".")
} else {
  message("consommation.txt non trouvé : création du fichier à partir des données")
  conso <- data.frame(
    consommation = c(5.7, 5.8, 6.1, 7.1, 9.5, 9.3, 6.4, 6.6, 7, 6.7, 7.1, 7.8, 8.4, 9.9,
                     7.2, 10, 10.7, 8.3, 8.7, 10.3, 10.6, 10.9, 12.1, 10.8, 10.3, 11.3, 10.6, 13.2),
    cylindree    = c(846, 993, 899, 1331, 1983, 1580, 1100, 1197, 1248, 1298, 1398, 1498, 1560, 1598,
                     1660, 1796, 1896, 1997, 2098, 2198, 2295, 2393, 2497, 2598, 2698, 2799, 2997, 3200),
    puissance    = c(32, 39, 29, 55, 85, 65, 55, 50, 50, 56, 60, 51, 66, 58,
                     69, 73, 69, 76, 95, 105, 101, 104, 98, 112, 117, 114, 142, 152),
    poids        = c(650, 790, 730, 1010, 1075, 1080, 778, 788, 717, 846, 922, 1042, 870, 1107,
                     919, 1160, 1207, 1133, 1224, 1464, 1274, 1332, 1456, 1414, 1655, 1454, 1592, 1738),
    carburant    = c(0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1,
                     1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1)
  )
  write.table(conso, "consommation.txt", sep = "\t", row.names = FALSE, quote = FALSE)
  conso <- read.table("consommation.txt", header = TRUE, sep = "", dec = ".")
}
head(conso)   # premières observations
str(conso)    # structure
dim(conso)    # dimensions (28 x 5 attendu)

# ---------------------------------------------------------------------
# 2. Statistiques descriptives, corrélations et nuages de points
# ---------------------------------------------------------------------

summary(conso)
table(conso$carburant)

quanti <- conso[, c("consommation", "cylindree", "puissance", "poids")]
round(cor(quanti), 3)

pairs(quanti, pch = 19, col = ifelse(conso$carburant == 1, "red", "steelblue"),
      main = "Matrice des nuages de points (rouge : carburant = 1)")

# Diagnostic de multicolinéarité : facteurs d'inflation de la variance (VIF = 1 / (1 - R²_j))
expl <- c("cylindree", "puissance", "poids", "carburant")
vif <- sapply(expl, function(v) {
  r2 <- summary(lm(as.formula(paste(v, "~", paste(setdiff(expl, v), collapse = "+"))),
                   data = conso))$r.squared
  1 / (1 - r2)
})
round(vif, 2)

# Interprétation :
# - Base : 28 véhicules, 5 variables ; consommation moyenne ≈ 8,87 L/100 km ; 15 véhicules ont carburant = 1 et 13 ont carburant = 0.
# - La consommation est fortement corrélée à chaque variable : r = 0,911 (cylindrée), 0,859 (puissance), 0,912 (poids).
# - Mais les explicatives sont très corrélées entre elles : cylindrée–puissance r = 0,979, cylindrée–poids r = 0,962, puissance–poids r = 0,938.
# - Les VIF le confirment : cylindree ≈ 44,1, puissance ≈ 26,0, poids ≈ 13,5 (tous > 10), carburant ≈ 1,7.
#
# → Problème de multicolinéarité sévère entre cylindrée, puissance et poids : les coefficients seront instables et leurs écarts-types gonflés.

# ---------------------------------------------------------------------
# 3. Modèle mathématique et estimation
# ---------------------------------------------------------------------
#
#  consommation_i = beta_0 + beta_1  cylindree_i + beta_2  puissance_i + beta_3  poids_i + beta_4  carburant_i + eps_i,    i=1,...,28 
#
# avec eps_i ~iid N(0,sigma^2).

modele_conso <- lm(consommation ~ cylindree + puissance + poids + carburant, data = conso)
summary(modele_conso)

# ---------------------------------------------------------------------
# 4. Équation estimée
# ---------------------------------------------------------------------

b <- round(coef(modele_conso), 5)
cat("consommation_hat =", b[1],
    "+", b[2], "* cylindree",
    "+", b[3], "* puissance",
    "+", b[4], "* poids",
    "+", b[5], "* carburant\n")

# Équation estimée :
#
# consommation^ = 2,544 + 0,002318 cylindree - 0,03085 puissance + 0,003478 poids + 1,0229 carburant
#
# Interprétation (toutes choses égales par ailleurs) :
# - Poids : beta^_3 = 0,003478. Un kilogramme supplémentaire augmente la consommation de 0,0035 L/100 km en moyenne,
#   soit +0,35 L/100 km pour 100 kg de plus, à cylindrée, puissance et carburant fixés.
# - Carburant : beta^_4 = 1,023. À cylindrée, puissance et poids égaux, un véhicule codé 1 consomme en moyenne
#   1,02 L/100 km de plus qu'un véhicule codé 0 (modalité de référence).
# - *Remarque :* le coefficient de la puissance est négatif (−0,031), ce qui est contre-intuitif : c'est un effet de la multicolinéarité.

# ---------------------------------------------------------------------
# 5. Significativité des variables, R^2, R^2 ajusté et test global
# ---------------------------------------------------------------------

s <- summary(modele_conso)
coefs <- s$coefficients
coefs
cat("\nVariables significatives à 5 % :",
    rownames(coefs)[coefs[, 4] < 0.05 & rownames(coefs) != "(Intercept)"], "\n")
cat("R²         =", round(s$r.squared, 4), "\n")
cat("R² ajusté  =", round(s$adj.r.squared, 4), "\n")
f <- s$fstatistic
cat("F =", round(f[1], 2), "  p-value =", signif(pf(f[1], f[2], f[3], lower.tail = FALSE), 4), "\n")

# Résultats :
#
# | Variable | Estimation | Écart-type | t | p-value | Significative à 5 % ? |
# |---|---|---|---|---|---|
# | (Intercept) | 2,544 | 0,651 | 3,91 | 0,0007 | oui |
# | cylindree | 0,002318 | 0,001343 | 1,73 | 0,098 | non |
# | puissance | −0,03085 | 0,02124 | −1,45 | 0,160 | non |
# | poids | 0,003478 | 0,001593 | 2,18 | 0,039 | oui |
# | carburant | 1,0229 | 0,3393 | 3,01 | 0,006 | oui |
#
# - Variables significatives au seuil de 5 % : poids et carburant ; cylindree et puissance ne le sont pas.
# - R^2 = 0,906 : le modèle explique environ 90,6 % de la variabilité de la consommation.
# - R^2 ajusté = 0,890 : il reste élevé, même en tenant compte du nombre de variables.
# - Test de Fisher : F = 55,73 avec (4 ; 23) ddl, p ≈ 1,7×10⁻¹¹ < 0,05 → le modèle est globalement très significatif.
# - Écart-type résiduel : σ̂ ≈ 0,689 L/100 km.
# - Le modèle est très significatif, alors que cylindrée et puissance, pourtant très corrélées à la consommation, ne le sont pas individuellement : c'est le signe typique de la multicolinéarité.

# ---------------------------------------------------------------------
# 6. Analyse de la variance avec anova()
# ---------------------------------------------------------------------

anova(modele_conso)

# Différence avec les tests de summary() :
# - anova() utilise des sommes des carrés séquentielles (type I) : chaque ligne mesure l'apport d'une variable après les variables
#   placées avant elle dans la formule. Le résultat dépend donc de l'ordre des variables (sauf pour la dernière).
# - Les tests de Student de summary() évaluent chaque variable en présence de toutes les autres (contribution marginale, type III).
# - Seule la dernière variable a le même test dans les deux tableaux (F = t^2).
#
# Résultats (SC séquentielles, résiduelle = 10,91 sur 23 ddl) :
#
# | Variable | SC | F | p-value |
# |---|---|---|---|
# | cylindree | 96,72 | 203,9 | 6,4×10⁻¹³ |
# | puissance | 2,89 | 6,09 | 0,021 |
# | poids | 1,83 | 3,85 | 0,062 |
# | carburant | 4,31 | 9,09 | 0,006 |
#
# → Dans anova(), cylindree est très significative car, placée en premier, elle capte presque toute la variance commune.
# Dans summary(), elle ne l'est pas (p = 0,098). À l'inverse, poids est significatif dans summary() (p = 0,039) mais pas ici (p = 0,062).
# Pour carburant (dernière variable), on retrouve le même test : F = 9,09 = t^2 = 3,015^2.

# Illustration : changer l'ordre des variables modifie le tableau d'ANOVA
anova(lm(consommation ~ poids + puissance + cylindree + carburant, data = conso))

# ---------------------------------------------------------------------
# 7. Analyse des résidus
# ---------------------------------------------------------------------

par(mfrow = c(2, 2))
plot(modele_conso)
par(mfrow = c(1, 1))

res <- residuals(modele_conso)
par(mfrow = c(1, 2))
hist(res, main = "Histogramme des résidus", col = "lightblue", xlab = "Résidus", freq = FALSE)
curve(dnorm(x, mean(res), sd(res)), add = TRUE, col = "red", lwd = 2)
qqnorm(res); qqline(res, col = "red")
par(mfrow = c(1, 1))

shapiro.test(res)   # H0 : normalité des résidus

# Lecture des graphiques :
# - *Residuals vs Fitted* : les résidus doivent être répartis au hasard autour de 0, sans forme particulière ; c'est ce qui rend la linéarité plausible.
# - *Normal Q-Q* : points proches de la droite. Le test de Shapiro-Wilk donne W = 0,970 et p = 0,586 > 0,05, donc on ne rejette pas la normalité des résidus.
# - *Scale-Location* : la dispersion doit rester à peu près constante, ce qui rend l'homoscédasticité plausible.
# - *Residuals vs Leverage* : la plus grande distance de Cook vaut ≈ 0,21 (observation 25), bien en dessous de 0,5. Aucune observation n'est trop influente.
#
# Conclusion : les hypothèses usuelles du modèle linéaire semblent plausibles. La principale limite est la multicolinéarité.
# On pourrait par exemple retirer cylindree ou puissance, puis comparer les modèles.

# #####################################################################
# EXERCICE 3 — RÉGRESSION LOGISTIQUE SUR MTCARS
# #####################################################################
#

# ---------------------------------------------------------------------
# 1. Chargement, structure et nature des variables
# ---------------------------------------------------------------------

data(mtcars)
head(mtcars)
str(mtcars)
summary(mtcars[, c("am", "wt")])

# Nature des variables :
# - am : variable qualitative binaire (0 = automatique, 1 = manuelle), stockée en numérique → variable réponse.
# - wt : variable quantitative continue (poids en milliers de livres) → variable explicative.

# ---------------------------------------------------------------------
# 2. Effectifs de am et distribution de wt selon la transmission
# ---------------------------------------------------------------------

table(mtcars$am)
prop.table(table(mtcars$am))

boxplot(wt ~ am, data = mtcars, col = c("salmon", "lightgreen"),
        names = c("Automatique (0)", "Manuelle (1)"),
        main = "Poids selon le type de transmission", ylab = "Poids (milliers de livres)")
tapply(mtcars$wt, mtcars$am, summary)

# Commentaire : 19 voitures automatiques et 13 manuelles. Les voitures à transmission manuelle sont nettement plus légères
# (poids médian ≈ 2,3 contre ≈ 3,5 milliers de livres). Le poids semble donc un bon prédicteur du type de transmission.

# ---------------------------------------------------------------------
# 3. Justification de la régression logistique et modèle
# ---------------------------------------------------------------------
#
# La variable am est binaire : une régression linéaire est inadaptée (prédictions hors de [0 ; 1], erreurs non normales,
# variance non constante p(1-p)). On modélise donc Y_i ~ B(p_i) avec la fonction de lien logit :
#
#   log(p_i / (1 - p_i)) = beta_0 + beta_1 * wt_i
#   <=>  p_i = P(am_i = 1 | wt_i) = exp(beta_0 + beta_1*wt_i) / (1 + exp(beta_0 + beta_1*wt_i))

# ---------------------------------------------------------------------
# 4. Estimation avec glm()
# ---------------------------------------------------------------------

modele_log <- glm(am ~ wt, data = mtcars, family = binomial(link = "logit"))
summary(modele_log)

# ---------------------------------------------------------------------
# 5. Équation estimée et test de Wald
# ---------------------------------------------------------------------

b <- coef(modele_log)
cat("logit(p_hat) =", round(b[1], 3), "+", round(b[2], 3), "* wt\n\n")

wald <- summary(modele_log)$coefficients["wt", ]
z <- wald["Estimate"] / wald["Std. Error"]
cat("Statistique de Wald z =", round(z, 3), "  p-value =", signif(2 * pnorm(-abs(z)), 4), "\n")

# Équation estimée : log(frac{p^}{1-p^}) ≈ 12,04 - 4,02 x wt
#
# - Signe négatif de beta^_1 : plus la voiture est lourde, plus la probabilité d'avoir une transmission manuelle diminue.
# - Test de Wald : H_0 : beta_1 = 0 contre H_1 : beta_1 != 0, z = beta^_1 / se(beta^_1) ~ N(0,1) sous H_0.
#   La *p-value* (≈ 0,005) est inférieure à 0,05 → on rejette H_0 : le poids a un effet significatif sur le type de transmission.

# ---------------------------------------------------------------------
# 6. Odds ratio
# ---------------------------------------------------------------------

exp(coef(modele_log))
exp(confint.default(modele_log))   # IC à 95 % (Wald) des odds ratios

# Interprétation : OR = exp(beta^_1) ≈ exp(-4,02) ≈ 0,018.
# Lorsque le poids augmente de 1 000 livres, la cote (*odds*) d'avoir une transmission manuelle est multipliée par ≈ 0,018,
# c'est-à-dire qu'elle diminue d'environ 98 %. L'OR étant < 1 (et son IC ne contenant pas 1), le poids est un facteur défavorable à la boîte manuelle.

# ---------------------------------------------------------------------
# 7. Prédiction pour wt = 3
# ---------------------------------------------------------------------

p3 <- predict(modele_log, newdata = data.frame(wt = 3), type = "response")
p3
classe <- ifelse(p3 >= 0.5, 1, 0)
cat("Probabilité estimée :", round(p3, 4), " -> classe prédite (seuil 0,5) :", classe,
    ifelse(classe == 1, "(manuelle)", "(automatique)"), "\n")

# Courbe logistique estimée
plot(mtcars$wt, mtcars$am, pch = 19, col = "steelblue",
     xlab = "Poids (milliers de livres)", ylab = "P(transmission manuelle)",
     main = "Courbe de régression logistique")
curve(predict(modele_log, data.frame(wt = x), type = "response"), add = TRUE, col = "red", lwd = 2)
abline(v = 3, h = 0.5, lty = 2, col = "grey40")

# Probabilité estimée vs classe prédite :
# - La probabilité estimée p^ ≈ 0,49 est une valeur continue dans [0 ; 1] : c'est la probabilité qu'une voiture de 3 000 livres
#   ait une transmission manuelle selon le modèle.
# - La classe prédite est une décision binaire obtenue en comparant p^ à un seuil (souvent 0,5) :
#   ici p^ < 0,5 → classe 0 (automatique). Comme p^ est très proche de 0,5, la prédiction est très incertaine :
#   une voiture de ce poids est presque « à la frontière » entre les deux types.

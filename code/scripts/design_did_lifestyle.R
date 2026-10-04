# Conditional (doubly-robust) DiD with baseline lifestyle covariates, issue #7. Exploratory.
# Run in research-container from /home/repo-intro:  Rscript scripts/design_did_lifestyle.R
# Compares unconditional (reg, no covariates) vs DR with covariates on the SAME samples. Reference e=-1 (universal base period).
#  balanced:   users observed 2018Q1-2022Q4, adopters 2019Q1-2021Q4, e in [-4,4], post = e 1..4
#  unbalanced: full panel; adopters need >=6 quarters of pre-history so the baseline window (first 4 quarters) precedes adoption; e in [-8,8], post = 1..8
suppressMessages({library(did); library(dplyr)})
O <- "analysis/outputs/"; I <- "build/interm/"
P <- merge(read.csv(paste0(I, "design_panel_q.csv")), read.csv(paste0(I, "design_covariates.csv")), by = "id")
COV <- ~ pc1 + pc2 + pc3 + pc4 + ln_n_b + age + inc + hh + female + college + white + diab + smoke + alc + svy_miss
T0 <- 2018*4+1; T1 <- 2022*4+4
OUT <- c(run_shoe_d = "Running shoe", run_any_d = "Running-related (keyword)", fit_gear_d = "Fitness gear", supp_d = "Supplements",
         med_d = "Medication", pet_d = "PLACEBO: pet", book_d = "PLACEBO: books", giftcard_d = "PLACEBO: gift cards",
         cable_d = "PLACEBO: cables/batteries", cleaning_d = "PLACEBO: cleaning", grocery_d = "PLACEBO: grocery/food",
         ln_n = "General: ln(1+#purchases)", ln_spend = "General: ln(1+spend)")

est <- function(df, gname, y, cond, balanced, emin, emax) {
  df$G <- ifelse(is.na(df[[gname]]), 0, df[[gname]])
  at <- att_gt(yname = y, tname = "t", idname = "id", gname = "G", data = df, xformla = if (cond) COV else ~1,
               control_group = "nevertreated", base_period = "universal", allow_unbalanced_panel = !balanced,
               bstrap = FALSE, cband = FALSE, est_method = if (cond) "dr" else "reg")
  es <- aggte(at, type = "dynamic", min_e = emin, max_e = emax, na.rm = TRUE, bstrap = FALSE, cband = FALSE)
  po <- aggte(at, type = "dynamic", min_e = 1, max_e = emax, na.rm = TRUE, bstrap = FALSE, cband = FALSE)
  list(es = data.frame(e = es$egt, att = es$att.egt, se = es$se.egt), post = c(po$overall.att, po$overall.se),
       nT = length(unique(df$id[df$G > 0])), nC = length(unique(df$id[df$G == 0])))
}
S <- list(); E <- list(); OV <- list()
for (sp in list(list("main_all", "s_g", "g_q"), list("main_clean", "s_g_clean", "g_clean_q"))) {
  base <- P[P[[sp[[2]]]] == 1, ]; gq <- base[[sp[[3]]]]
  for (pn in c("balanced", "unbalanced")) {
    if (pn == "balanced") {
      span <- base %>% group_by(id) %>% summarise(t0 = min(t), t1 = max(t)); ids <- span$id[span$t0 <= T0 & span$t1 >= T1]
      d <- base[(is.na(gq) | (gq >= 2019*4+1 & gq <= 2021*4+4)) & base$id %in% ids & base$t >= T0 & base$t <= T1, ]
      emin <- -4; emax <- 4
    } else {
      d <- base[is.na(gq) | (gq - base$t0 >= 6), ]; emin <- -8; emax <- 8
    }
    # overlap diagnostic: user-level logit of adoption on covariates
    u <- d %>% group_by(id) %>% slice(1) %>% ungroup(); u$adopt <- as.numeric(!is.na(u[[sp[[3]]]]))
    ps <- predict(glm(update(COV, adopt ~ .), data = u, family = binomial), type = "response")
    OV[[paste(sp[[1]], pn)]] <- data.frame(spec = sp[[1]], panel = pn, n_adopt = sum(u$adopt), n_ctrl = sum(1 - u$adopt),
        ps_mean_adopt = mean(ps[u$adopt == 1]), ps_mean_ctrl = mean(ps[u$adopt == 0]), ctrl_ps_p99 = quantile(ps[u$adopt == 0], .99), adopt_ps_gt90 = mean(ps[u$adopt == 1] > .9))
    for (y in names(OUT)) for (cond in c(FALSE, TRUE)) {
      r <- tryCatch(est(d, sp[[3]], y, cond, pn == "balanced", emin, emax), error = function(e) { message("FAIL ", sp[[1]], pn, y, cond, ": ", conditionMessage(e)); NULL })
      if (is.null(r)) next
      k <- paste(sp[[1]], pn, y, cond)
      pre <- r$es$att[r$es$e < -1]
      S[[k]] <- data.frame(spec = sp[[1]], panel = pn, outcome = y, name = OUT[[y]], cond = cond, post_att = r$post[1], post_se = r$post[2],
                           mean_pre = mean(pre), n_treated = r$nT, n_ctrl = r$nC)
      E[[k]] <- cbind(r$es, spec = sp[[1]], panel = pn, outcome = y, name = OUT[[y]], cond = cond)
      cat(k, sprintf("post=%.4f (%.4f) mean_pre=%.4f nT=%d nC=%d\n", r$post[1], r$post[2], mean(pre), r$nT, r$nC))
    }
  }
}
write.csv(bind_rows(S), paste0(O, "design_did_lifestyle_summary.csv"), row.names = FALSE)
write.csv(bind_rows(E), paste0(O, "design_did_lifestyle_eventstudy.csv"), row.names = FALSE)
write.csv(bind_rows(OV), paste0(O, "design_did_lifestyle_overlap.csv"), row.names = FALSE)

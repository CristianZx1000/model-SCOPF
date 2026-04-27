\ Model DCOPF_3b_copy
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
 
Subject To
 LCK_post[7]_caso6_w2[0]: Pg_post_caso6[0,7,2] + Pg_post_caso6[1,7,2]
   + Pg_post_caso6[2,7,2] + p_ens_post_caso6[0,7,2] - f_post_caso6[0,7,2]
   - f_post_caso6[1,7,2] - f_post_caso6[2,7,2] - f_post_caso6[3,7,2]
   - 0.5 Ploss_post_caso6[0,7,2] - 0.5 Ploss_post_caso6[1,7,2]
   - 0.5 Ploss_post_caso6[2,7,2] - 0.5 Ploss_post_caso6[3,7,2] = 0
 LCK_post[7]_caso6_w2[1]: p_ens_post_caso6[1,7,2] + f_post_caso6[0,7,2]
   - 0.5 Ploss_post_caso6[0,7,2] = 2.434
 LCK_post[7]_caso6_w2[2]: p_ens_post_caso6[2,7,2] + f_post_caso6[1,7,2]
   - 0.5 Ploss_post_caso6[1,7,2] = 2.225
 LCK_post[7]_caso6_w2[3]: p_ens_post_caso6[3,7,2] + f_post_caso6[2,7,2]
   - 0.5 Ploss_post_caso6[2,7,2] = 7.863
 LCK_post[7]_caso6_w2[4]: p_ens_post_caso6[4,7,2] + f_post_caso6[3,7,2]
   - f_post_caso6[4,7,2] - 0.5 Ploss_post_caso6[3,7,2]
   - 0.5 Ploss_post_caso6[4,7,2] = 0
 LCK_post[7]_caso6_w2[5]: p_ens_post_caso6[5,7,2] + f_post_caso6[4,7,2]
   - f_post_caso6[5,7,2] - 0.5 Ploss_post_caso6[4,7,2]
   - 0.5 Ploss_post_caso6[5,7,2] = 0.63
 LCK_post[7]_caso6_w2[6]: p_ens_post_caso6[6,7,2] + f_post_caso6[5,7,2]
   - f_post_caso6[6,7,2] - 0.5 Ploss_post_caso6[5,7,2]
   - 0.5 Ploss_post_caso6[6,7,2] = 0.005
 LCK_post[7]_caso6_w2[7]: Pg_post_caso6[3,7,2] + Pg_post_caso6[4,7,2]
   + Pg_post_caso6[5,7,2] + p_ens_post_caso6[7,7,2] + f_post_caso6[6,7,2]
   - 0.5 Ploss_post_caso6[6,7,2] = -4.2121715061552
 f_lin_0_7_post_caso6_w2: Ploss_post_caso6[0,7,2] = 0
 f_lin_1_7_post_caso6_w2: Ploss_post_caso6[1,7,2] = 0
 f_lin_2_7_post_caso6_w2: Ploss_post_caso6[2,7,2]
   - 0.00733979301291914 df_post_caso6[2,0,7,2]
   - 0.0220193790387574 df_post_caso6[2,1,7,2] = 0
 f_lin_3_7_post_caso6_w2: Ploss_post_caso6[3,7,2] = 0
 f_lin_4_7_post_caso6_w2: Ploss_post_caso6[4,7,2]
   - 0.12104217682701 df_post_caso6[4,0,7,2]
   - 0.3631265304810299 df_post_caso6[4,1,7,2] = 0
 f_lin_5_7_post_caso6_w2: Ploss_post_caso6[5,7,2]
   - 3.5474323001259754e-04 df_post_caso6[5,0,7,2]
   - 0.00106422969003779 df_post_caso6[5,1,7,2] = 0
 f_lin_6_7_post_caso6_w2: Ploss_post_caso6[6,7,2]
   - 0.00330781279590593 df_post_caso6[6,0,7,2]
   - 0.00992343838771778 df_post_caso6[6,1,7,2] = 0
 fp_max_post[7]_caso6_w2[2]: - fp_post_caso6[2,7,2]
   + 32.92 n_lf_post_caso6[2,7,2] >= 0
 fp_max_post[7]_caso6_w2[4]: - fp_post_caso6[4,7,2]
   + 21.19 n_lf_post_caso6[4,7,2] >= 0
 fp_max_post[7]_caso6_w2[5]: - fp_post_caso6[5,7,2]
   + 14.06 n_lf_post_caso6[5,7,2] >= 0
 fn_max_post[7]_caso6_w2[2]: - fn_post_caso6[2,7,2]
   - 32.92 n_lf_post_caso6[2,7,2] >= -32.92
 fn_max_post[7]_caso6_w2[4]: - fn_post_caso6[4,7,2]
   - 21.19 n_lf_post_caso6[4,7,2] >= -21.19
 fn_max_post[7]_caso6_w2[5]: - fn_post_caso6[5,7,2]
   - 14.06 n_lf_post_caso6[5,7,2] >= -14.06
 f0_post[7]_2_caso6_w2: - fp_post_caso6[2,7,2] - fn_post_caso6[2,7,2]
   + df_post_caso6[2,0,7,2] + df_post_caso6[2,1,7,2] = 0
 f0_post[7]_4_caso6_w2: - fp_post_caso6[4,7,2] - fn_post_caso6[4,7,2]
   + df_post_caso6[4,0,7,2] + df_post_caso6[4,1,7,2] = 0
 f0_post[7]_5_caso6_w2: - fp_post_caso6[5,7,2] - fn_post_caso6[5,7,2]
   + df_post_caso6[5,0,7,2] + df_post_caso6[5,1,7,2] = 0
 f1_post[7]_caso6_w2[2]: f_post_caso6[2,7,2] - fp_post_caso6[2,7,2]
   + fn_post_caso6[2,7,2] = 0
 f1_post[7]_caso6_w2[4]: f_post_caso6[4,7,2] - fp_post_caso6[4,7,2]
   + fn_post_caso6[4,7,2] = 0
 f1_post[7]_caso6_w2[5]: f_post_caso6[5,7,2] - fp_post_caso6[5,7,2]
   + fn_post_caso6[5,7,2] = 0
 df_post[7]_line2_seg0_min_caso6_w2: df_post_caso6[2,0,7,2]
   - 16.46 n_df_post_caso6[2,0,7,2] >= 0
 df_post[7]_line2_seg1_max_caso6_w2: - df_post_caso6[2,1,7,2]
   + 16.46 n_df_post_caso6[2,0,7,2] >= 0
 df_post[7]_line4_seg0_min_caso6_w2: df_post_caso6[4,0,7,2]
   - 10.595 n_df_post_caso6[4,0,7,2] >= 0
 df_post[7]_line4_seg1_max_caso6_w2: - df_post_caso6[4,1,7,2]
   + 10.595 n_df_post_caso6[4,0,7,2] >= 0
 df_post[7]_line6_seg0_max_caso6_w2: - df_post_caso6[6,0,7,2] >= -7.03
 df_post[7]_line6_seg1_max_caso6_w2: - df_post_caso6[6,1,7,2]
   + 7.03 n_df_post_caso6[6,0,7,2] >= 0
 P_min_post[7]_caso6_w2[0]: Pg_post_caso6[0,7,2] >= 4
 P_min_post[7]_caso6_w2[1]: Pg_post_caso6[1,7,2] >= 5
 P_min_post[7]_caso6_w2[2]: Pg_post_caso6[2,7,2] >= 0.5
Bounds
 Pg_post_caso6[0,7,2] free
 Pg_post_caso6[1,7,2] free
 Pg_post_caso6[2,7,2] free
 f_post_caso6[0,7,2] free
 f_post_caso6[1,7,2] free
 f_post_caso6[2,7,2] free
 f_post_caso6[3,7,2] free
 f_post_caso6[4,7,2] free
 f_post_caso6[5,7,2] free
 f_post_caso6[6,7,2] free
 fp_post_caso6[2,7,2] free
 fp_post_caso6[4,7,2] free
 fp_post_caso6[5,7,2] free
 fn_post_caso6[2,7,2] free
 fn_post_caso6[4,7,2] free
 fn_post_caso6[5,7,2] free
 Ploss_post_caso6[0,7,2] free
 Ploss_post_caso6[1,7,2] free
 Ploss_post_caso6[2,7,2] free
 Ploss_post_caso6[3,7,2] free
 Ploss_post_caso6[4,7,2] free
 Ploss_post_caso6[5,7,2] free
 Ploss_post_caso6[6,7,2] free
 df_post_caso6[2,0,7,2] free
 df_post_caso6[2,1,7,2] free
 df_post_caso6[4,0,7,2] free
 df_post_caso6[4,1,7,2] free
 df_post_caso6[5,1,7,2] free
 df_post_caso6[6,0,7,2] free
 df_post_caso6[6,1,7,2] free
Binaries
 n_lf_post_caso6[2,7,2] n_lf_post_caso6[4,7,2] n_lf_post_caso6[5,7,2]
 n_df_post_caso6[2,0,7,2] n_df_post_caso6[4,0,7,2] n_df_post_caso6[6,0,7,2]
End

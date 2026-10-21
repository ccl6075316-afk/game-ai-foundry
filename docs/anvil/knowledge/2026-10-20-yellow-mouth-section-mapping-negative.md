# Negative trial: source jaw mapping can introduce transverse head ridges

Yellow croaker093 restores side-jaw thickness but introduces head rings absent from the baseline. It remains rejected for production. The exact inputs, diagnostics and current state live in Fish `experiments/blender-fish/yellow-mouth-093/completion.validation.json`.

A positive finite-difference Jacobian only excludes sampled folds; it does not prove smooth geometry or correct normals. Recomputing only normals did not remove the new silhouette ripples. Limiting sigma5.5 target smoothing to2px relative to sigma1.1 also failed visually. Do not recommend either diagnostic as a verified fix.

Separate the preoral source-alpha stair-step target from oral anchor order. In this trial102 oral stations have estimated high<upper-cleft threshold, while max(denominator,1e-5) masks the invalid ordering. A no-write identity control must reproduce original vertices before applying new targets. Dense cross sections need true rim identities and upper/lower endpoint ownership; another fish's approximate model_path cannot define these by assumption.

Keep source canvas and opening fixed. Use actual grey baseline/candidate views and trace section contributions. Restore geometry smoothness before texture tuning; colors cannot repair shallow planar mouth topology. All fin/body/runtime gates can pass while shape remains unacceptable. Current trial was not installed and no final repair is claimed.

"""Explicit native/actual posed vertex correspondence for finite fin authoring."""
import numpy as np

def native_to_actual(native,actual,scale,maximum_rest_error_m=5e-6):
    native=np.asarray(native,float)*scale;actual=np.asarray(actual,float)
    assert native.ndim==2 and native.shape==actual.shape and native.shape[1]==3
    assert np.isfinite(native).all()and np.isfinite(actual).all()
    distances=np.linalg.norm(native[:,None,:]-actual[None,:,:],axis=2)
    mapping=np.argmin(distances,axis=1);errors=distances[np.arange(len(native)),mapping]
    assert len(set(mapping.tolist()))==len(native),'Ambiguous native/posed vertex correspondence'
    assert errors.max()<maximum_rest_error_m,'Actual rest pose does not match native vertices'
    # Even a small absolute error is ambiguous when separate vertices nearly
    # coincide. Require a clear nearest identity, not an arbitrary argmin tie.
    runner_up=np.partition(distances,1,axis=1)[:,1]
    assert np.all(runner_up>np.maximum(errors*4,1e-9)),'Insufficient identity separation'
    return mapping

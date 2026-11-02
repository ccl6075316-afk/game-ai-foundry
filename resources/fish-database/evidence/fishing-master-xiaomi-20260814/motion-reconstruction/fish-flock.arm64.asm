
; 0x207ab6c FishFlock.FishData$$get_rotFwd | Vector3 get_rotFwd()
0207ab6c: ldr      d0, [x0]
0207ab70: ldur     d2, [x0, #0xc]
0207ab74: ldr      s1, [x0, #8]
0207ab78: ldr      s3, [x0, #0x14]
0207ab7c: fadd     v2.2s, v0.2s, v2.2s
0207ab80: fsub     v0.2s, v2.2s, v0.2s
0207ab84: fadd     s3, s1, s3
0207ab88: fsub     s2, s3, s1
0207ab8c: mov      s1, v0.s[1]
0207ab90: ret

; 0x207ab94 FishFlock.FishGroup$$Init | void Init(FishFlockController controller)
0207ab94: str      x30, [sp, #-0x20]!
0207ab98: stp      x20, x19, [sp, #0x10]
0207ab9c: mov      x19, x0
0207aba0: str      x1, [x0, #0xa8]!
0207aba4: mov      x20, x1
0207aba8: bl       #0x18ddb68
0207abac: cbz      x20, #0x207ac40
0207abb0: mov      x0, x20
0207abb4: mov      x1, xzr
0207abb8: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207abbc: cbz      x0, #0x207ac40
0207abc0: mov      x1, xzr
0207abc4: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207abc8: stp      s0, s1, [x19, #0x94]
0207abcc: str      s2, [x19, #0x9c]
0207abd0: ldr      s0, [x19, #0x44]
0207abd4: ldr      w8, [x20, #0x30]
0207abd8: ldrb     w9, [x19, #0x54]
0207abdc: mov      w10, #0xc5ac
0207abe0: movk     w10, #0x3727, lsl #16
0207abe4: str      s0, [x19, #0x4c]
0207abe8: str      w8, [x19, #0x20]
0207abec: str      w10, [x19, #0x48]
0207abf0: cbz      w9, #0x207ac08
0207abf4: ldr      x0, [x19, #0x58]
0207abf8: cbz      x0, #0x207ac40
0207abfc: mov      x1, xzr
0207ac00: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207ac04: b        #0x207ac2c
0207ac08: mov      w1, #1
0207ac0c: mov      x0, x19
0207ac10: bl       #0x207ac48 ; FishFlock.FishGroup$$GeneratePath
0207ac14: ldr      x8, [x19, #0x78]
0207ac18: cbz      x8, #0x207ac40
0207ac1c: ldr      w9, [x8, #0x18]
0207ac20: cbz      w9, #0x207ac44
0207ac24: ldp      s0, s1, [x8, #0x20]
0207ac28: ldr      s2, [x8, #0x28]
0207ac2c: stp      s0, s1, [x19, #0x94]
0207ac30: str      s2, [x19, #0x9c]
0207ac34: ldp      x20, x19, [sp, #0x10]
0207ac38: ldr      x30, [sp], #0x20
0207ac3c: ret
0207ac40: bl       #0x18dde20
0207ac44: bl       #0x18dde28

; 0x207aebc FishFlock.FishGroup$$UpdateGroupAnchor | void UpdateGroupAnchor()
0207aebc: sub      sp, sp, #0x90
0207aec0: stp      d15, d14, [sp, #0x30]
0207aec4: stp      d13, d12, [sp, #0x40]
0207aec8: stp      d11, d10, [sp, #0x50]
0207aecc: stp      d9, d8, [sp, #0x60]
0207aed0: str      x30, [sp, #0x70]
0207aed4: stp      x20, x19, [sp, #0x80]
0207aed8: adrp     x20, #0x3ed5000
0207aedc: ldrb     w8, [x20, #0x4d4]
0207aee0: mov      x19, x0
0207aee4: tbnz     w8, #0, #0x207aefc
0207aee8: adrp     x0, #0x3bf7000
0207aeec: ldr      x0, [x0, #0x468]
0207aef0: bl       #0x18ddbc4
0207aef4: mov      w8, #1
0207aef8: strb     w8, [x20, #0x4d4]
0207aefc: ldr      x0, [x19, #0xa8]
0207af00: cbz      x0, #0x207b2d0
0207af04: mov      x1, xzr
0207af08: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207af0c: cbz      x0, #0x207b2d0
0207af10: mov      x1, xzr
0207af14: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207af18: ldr      x0, [x19, #0xa8]
0207af1c: cbz      x0, #0x207b2d0
0207af20: ldr      s11, [x0, #0x20]
0207af24: mov      x1, xzr
0207af28: mov      v9.16b, v0.16b
0207af2c: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207af30: cbz      x0, #0x207b2d0
0207af34: mov      x1, xzr
0207af38: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207af3c: ldr      x0, [x19, #0xa8]
0207af40: cbz      x0, #0x207b2d0
0207af44: ldr      s12, [x0, #0x20]
0207af48: mov      x1, xzr
0207af4c: mov      v13.16b, v0.16b
0207af50: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207af54: cbz      x0, #0x207b2d0
0207af58: mov      x1, xzr
0207af5c: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207af60: ldr      x0, [x19, #0xa8]
0207af64: cbz      x0, #0x207b2d0
0207af68: ldr      s10, [x0, #0x24]
0207af6c: mov      x1, xzr
0207af70: mov      v8.16b, v1.16b
0207af74: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207af78: cbz      x0, #0x207b2d0
0207af7c: mov      x1, xzr
0207af80: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207af84: ldr      x0, [x19, #0xa8]
0207af88: cbz      x0, #0x207b2d0
0207af8c: ldr      s15, [x0, #0x24]
0207af90: mov      x1, xzr
0207af94: mov      v14.16b, v1.16b
0207af98: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207af9c: cbz      x0, #0x207b2d0
0207afa0: mov      x1, xzr
0207afa4: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207afa8: ldr      x0, [x19, #0xa8]
0207afac: str      s2, [sp, #0x7c]
0207afb0: cbz      x0, #0x207b2d0
0207afb4: ldr      s0, [x0, #0x28]
0207afb8: mov      x1, xzr
0207afbc: str      s0, [sp, #0x78]
0207afc0: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207afc4: cbz      x0, #0x207b2d0
0207afc8: mov      x1, xzr
0207afcc: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207afd0: ldr      x0, [x19, #0xa8]
0207afd4: str      s2, [sp, #0x24]
0207afd8: cbz      x0, #0x207b2d0
0207afdc: ldr      s0, [x0, #0x28]
0207afe0: mov      x1, xzr
0207afe4: stp      s15, s14, [sp, #0x28]
0207afe8: str      s0, [sp, #0x20]
0207afec: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207aff0: cbz      x0, #0x207b2d0
0207aff4: mov      x1, xzr
0207aff8: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207affc: ldrb     w8, [x19, #0x54]
0207b000: mov      v6.16b, v0.16b
0207b004: mov      v14.16b, v1.16b
0207b008: mov      v15.16b, v2.16b
0207b00c: cbz      w8, #0x207b0b4
0207b010: str      q6, [sp, #0x10]
0207b014: adrp     x8, #0x3bf7000
0207b018: ldr      x8, [x8, #0x468]
0207b01c: ldr      x20, [x19, #0x58]
0207b020: ldr      x0, [x8]
0207b024: ldr      w8, [x0, #0xe0]
0207b028: cbnz     w8, #0x207b030
0207b02c: bl       #0x18ddcfc
0207b030: mov      x0, x20
0207b034: mov      x1, xzr
0207b038: mov      x2, xzr
0207b03c: bl       #0x390f060 ; UnityEngine.Object$$op_Inequality
0207b040: ldr      q6, [sp, #0x10]
0207b044: tbz      w0, #0, #0x207b208
0207b048: ldr      x0, [x19, #0x58]
0207b04c: stp      s8, s10, [sp, #0xc]
0207b050: cbz      x0, #0x207b2d0
0207b054: mov      x1, xzr
0207b058: mov      v8.16b, v12.16b
0207b05c: mov      v12.16b, v13.16b
0207b060: mov      v13.16b, v11.16b
0207b064: mov      v11.16b, v9.16b
0207b068: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207b06c: ldur     d9, [x19, #0x94]
0207b070: ldr      s10, [x19, #0x9c]
0207b074: mov      x0, xzr
0207b078: mov      v0.s[1], v1.s[0]
0207b07c: fsub     v14.2s, v0.2s, v9.2s
0207b080: fsub     s15, s2, s10
0207b084: bl       #0x39070b8 ; UnityEngine.Time$$get_deltaTime
0207b088: ldr      s1, [x19, #0x6c]
0207b08c: fmul     v2.2s, v14.2s, v0.s[0]
0207b090: fmul     s0, s15, s0
0207b094: fmul     v2.2s, v2.2s, v1.s[0]
0207b098: fadd     v6.2s, v9.2s, v2.2s
0207b09c: mov      v9.16b, v11.16b
0207b0a0: mov      v11.16b, v13.16b
0207b0a4: mov      v13.16b, v12.16b
0207b0a8: mov      v12.16b, v8.16b
0207b0ac: ldr      s8, [sp, #0xc]
0207b0b0: b        #0x207b1f8
0207b0b4: ldr      x8, [x19, #0x78]
0207b0b8: cbz      x8, #0x207b2d0
0207b0bc: ldr      x10, [x8, #0x18]
0207b0c0: cbz      x10, #0x207b208
0207b0c4: ldrsw    x9, [x19, #0x90]
0207b0c8: stp      s9, s10, [sp, #0xc]
0207b0cc: cmp      w9, w10
0207b0d0: b.hs     #0x207b2d4
0207b0d4: mov      w10, #0xc
0207b0d8: adrp     x20, #0x3ed3000
0207b0dc: madd     x8, x9, x10, x8
0207b0e0: ldr      d14, [x19, #0x98]
0207b0e4: ldr      s15, [x19, #0x94]
0207b0e8: ldrb     w9, [x20, #0x932]
0207b0ec: ldr      s10, [x8, #0x20]
0207b0f0: ldur     d9, [x8, #0x24]
0207b0f4: cbnz     w9, #0x207b10c
0207b0f8: adrp     x0, #0x3bf8000
0207b0fc: ldr      x0, [x0, #0xc80]
0207b100: bl       #0x18ddbc4
0207b104: mov      w8, #1
0207b108: strb     w8, [x20, #0x932]
0207b10c: adrp     x8, #0x3bf8000
0207b110: ldr      x8, [x8, #0xc80]
0207b114: fsub     s10, s15, s10
0207b118: fsub     v9.2s, v14.2s, v9.2s
0207b11c: ldr      x0, [x8]
0207b120: ldr      w8, [x0, #0xe0]
0207b124: cbnz     w8, #0x207b12c
0207b128: bl       #0x18ddcfc
0207b12c: fmul     s0, s10, s10
0207b130: fmul     v1.2s, v9.2s, v9.2s
0207b134: fadd     s0, s0, s1
0207b138: mov      s1, v1.s[1]
0207b13c: fadd     s0, s0, s1
0207b140: fsqrt    s0, s0
0207b144: fmov     s1, #1.00000000
0207b148: fcmp     s0, s1
0207b14c: b.pl     #0x207b1a0
0207b150: ldr      w9, [x19, #0x90]
0207b154: ldr      x8, [x19, #0x78]
0207b158: add      w9, w9, #1
0207b15c: str      w9, [x19, #0x90]
0207b160: cbz      x8, #0x207b2d0
0207b164: ldr      w8, [x8, #0x18]
0207b168: cmp      w9, w8
0207b16c: b.lt     #0x207b1a0
0207b170: ldrb     w9, [x19, #0x68]
0207b174: cbz      w9, #0x207b188
0207b178: mov      w1, #1
0207b17c: mov      x0, x19
0207b180: bl       #0x207ac48 ; FishFlock.FishGroup$$GeneratePath
0207b184: b        #0x207b1a0
0207b188: ldrb     w9, [x19, #0x80]
0207b18c: cbz      w9, #0x207b198
0207b190: str      wzr, [x19, #0x90]
0207b194: b        #0x207b1a0
0207b198: sub      w8, w8, #1
0207b19c: str      w8, [x19, #0x90]
0207b1a0: ldr      x8, [x19, #0x78]
0207b1a4: cbz      x8, #0x207b2d0
0207b1a8: ldrsw    x9, [x19, #0x90]
0207b1ac: ldr      w10, [x8, #0x18]
0207b1b0: cmp      w9, w10
0207b1b4: b.hs     #0x207b2d4
0207b1b8: mov      w10, #0xc
0207b1bc: madd     x8, x9, x10, x8
0207b1c0: ldur     d9, [x19, #0x94]
0207b1c4: ldr      s10, [x19, #0x9c]
0207b1c8: ldr      d0, [x8, #0x20]
0207b1cc: ldr      s1, [x8, #0x28]
0207b1d0: mov      x0, xzr
0207b1d4: fsub     v14.2s, v0.2s, v9.2s
0207b1d8: fsub     s15, s1, s10
0207b1dc: bl       #0x39070b8 ; UnityEngine.Time$$get_deltaTime
0207b1e0: ldr      s1, [x19, #0x6c]
0207b1e4: fmul     v2.2s, v14.2s, v0.s[0]
0207b1e8: fmul     s0, s15, s0
0207b1ec: fmul     v2.2s, v2.2s, v1.s[0]
0207b1f0: fadd     v6.2s, v9.2s, v2.2s
0207b1f4: ldr      s9, [sp, #0xc]
0207b1f8: fmul     s0, s0, s1
0207b1fc: fadd     s15, s10, s0
0207b200: mov      s14, v6.s[1]
0207b204: ldr      s10, [sp, #0x10]
0207b208: ldrb     w8, [x19, #0x26]
0207b20c: cbz      w8, #0x207b2a4
0207b210: ldr      s4, [sp, #0x28]
0207b214: ldr      s5, [sp, #0x78]
0207b218: fmov     s0, #-0.50000000
0207b21c: fmov     s3, #0.50000000
0207b220: fmul     s0, s11, s0
0207b224: fmul     s3, s4, s3
0207b228: fmov     s4, #-0.50000000
0207b22c: fmul     s4, s5, s4
0207b230: fadd     s5, s9, s0
0207b234: ldr      s0, [sp, #0x2c]
0207b238: fmov     s1, #0.50000000
0207b23c: fmul     s1, s12, s1
0207b240: fadd     s1, s13, s1
0207b244: fadd     s3, s0, s3
0207b248: ldr      s0, [sp, #0x7c]
0207b24c: fmov     s2, #-0.50000000
0207b250: fcmp     s6, s1
0207b254: fmul     s2, s10, s2
0207b258: fcsel    s1, s1, s6, gt
0207b25c: fcmp     s6, s5
0207b260: fadd     s2, s8, s2
0207b264: fcsel    s6, s1, s5, pl
0207b268: fcmp     s14, s3
0207b26c: fadd     s0, s0, s4
0207b270: fcsel    s1, s3, s14, gt
0207b274: fcmp     s14, s2
0207b278: fcsel    s14, s1, s2, pl
0207b27c: fcmp     s15, s0
0207b280: b.mi     #0x207b2a8
0207b284: ldr      s1, [sp, #0x20]
0207b288: fmov     s0, #0.50000000
0207b28c: fmul     s0, s1, s0
0207b290: ldr      s1, [sp, #0x24]
0207b294: fadd     s0, s1, s0
0207b298: fcmp     s15, s0
0207b29c: fcsel    s0, s0, s15, gt
0207b2a0: b        #0x207b2a8
0207b2a4: mov      v0.16b, v15.16b
0207b2a8: stp      s6, s14, [x19, #0x94]
0207b2ac: str      s0, [x19, #0x9c]
0207b2b0: ldp      x20, x19, [sp, #0x80]
0207b2b4: ldr      x30, [sp, #0x70]
0207b2b8: ldp      d9, d8, [sp, #0x60]
0207b2bc: ldp      d11, d10, [sp, #0x50]
0207b2c0: ldp      d13, d12, [sp, #0x40]
0207b2c4: ldp      d15, d14, [sp, #0x30]
0207b2c8: add      sp, sp, #0x90
0207b2cc: ret
0207b2d0: bl       #0x18dde20
0207b2d4: bl       #0x18dde28

; 0x207ac48 FishFlock.FishGroup$$GeneratePath | void GeneratePath(bool isResetIndex = True)
0207ac48: stp      x30, x25, [sp, #-0x40]!
0207ac4c: stp      x24, x23, [sp, #0x10]
0207ac50: stp      x22, x21, [sp, #0x20]
0207ac54: stp      x20, x19, [sp, #0x30]
0207ac58: adrp     x21, #0x3ed5000
0207ac5c: ldrb     w8, [x21, #0x4d5]
0207ac60: mov      w20, w1
0207ac64: mov      x19, x0
0207ac68: tbnz     w8, #0, #0x207acb0
0207ac6c: adrp     x0, #0x3c28000
0207ac70: ldr      x0, [x0, #0x8d0]
0207ac74: bl       #0x18ddbc4
0207ac78: adrp     x0, #0x3bf7000
0207ac7c: ldr      x0, [x0, #0xe78]
0207ac80: bl       #0x18ddbc4
0207ac84: adrp     x0, #0x3bf7000
0207ac88: ldr      x0, [x0, #0xe90]
0207ac8c: bl       #0x18ddbc4
0207ac90: adrp     x0, #0x3c23000
0207ac94: ldr      x0, [x0, #0x9f8]
0207ac98: bl       #0x18ddbc4
0207ac9c: adrp     x0, #0x3c11000
0207aca0: ldr      x0, [x0, #0x768]
0207aca4: bl       #0x18ddbc4
0207aca8: mov      w8, #1
0207acac: strb     w8, [x21, #0x4d5]
0207acb0: ldr      x8, [x19, #0x70]
0207acb4: cbz      x8, #0x207aeb4
0207acb8: ldr      w1, [x8, #0x18]
0207acbc: adrp     x21, #0x3c11000
0207acc0: ldr      x21, [x21, #0x768]
0207acc4: cmp      w1, #1
0207acc8: b.lt     #0x207ad58
0207accc: ldr      x0, [x21]
0207acd0: bl       #0x18ddc6c
0207acd4: mov      x21, x19
0207acd8: str      x0, [x21, #0x78]!
0207acdc: mov      x1, x0
0207ace0: mov      x0, x21
0207ace4: bl       #0x18ddb68
0207ace8: ldur     x0, [x21, #-8]
0207acec: cbz      x0, #0x207aeb4
0207acf0: adrp     x23, #0x3bf7000
0207acf4: ldr      x23, [x23, #0xe90]
0207acf8: mov      x24, xzr
0207acfc: mov      x22, xzr
0207ad00: ldrsw    x8, [x0, #0x18]
0207ad04: cmp      x22, x8
0207ad08: b.ge     #0x207ae6c
0207ad0c: ldr      x2, [x23]
0207ad10: ldr      x25, [x21]
0207ad14: mov      w1, w22
0207ad18: bl       #0x281fec4 ; System.Collections.Generic.List<object>$$get_Item
0207ad1c: cbz      x0, #0x207aeb4
0207ad20: mov      x1, xzr
0207ad24: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207ad28: cbz      x25, #0x207aeb4
0207ad2c: ldr      w8, [x25, #0x18]
0207ad30: cmp      x22, x8
0207ad34: b.hs     #0x207aeb8
0207ad38: add      x8, x25, x24
0207ad3c: stp      s0, s1, [x8, #0x20]
0207ad40: str      s2, [x8, #0x28]
0207ad44: ldr      x0, [x19, #0x70]
0207ad48: add      x24, x24, #0xc
0207ad4c: add      x22, x22, #1
0207ad50: cbnz     x0, #0x207ad00
0207ad54: b        #0x207aeb4
0207ad58: ldr      x8, [x19, #0x88]
0207ad5c: cbz      x8, #0x207aeb4
0207ad60: ldr      w1, [x8, #0x18]
0207ad64: cmp      w1, #1
0207ad68: b.lt     #0x207adec
0207ad6c: ldr      x0, [x21]
0207ad70: bl       #0x18ddc6c
0207ad74: mov      x21, x19
0207ad78: str      x0, [x21, #0x78]!
0207ad7c: mov      x1, x0
0207ad80: mov      x0, x21
0207ad84: bl       #0x18ddb68
0207ad88: ldr      x0, [x21, #0x10]
0207ad8c: cbz      x0, #0x207aeb4
0207ad90: adrp     x24, #0x3c23000
0207ad94: ldr      x24, [x24, #0x9f8]
0207ad98: mov      x23, xzr
0207ad9c: mov      x22, xzr
0207ada0: ldrsw    x8, [x0, #0x18]
0207ada4: cmp      x22, x8
0207ada8: b.ge     #0x207ae6c
0207adac: ldr      x2, [x24]
0207adb0: ldr      x25, [x21]
0207adb4: mov      w1, w22
0207adb8: bl       #0x2871b38 ; System.Collections.Generic.List<Vector3>$$get_Item
0207adbc: cbz      x25, #0x207aeb4
0207adc0: ldr      w8, [x25, #0x18]
0207adc4: cmp      x22, x8
0207adc8: b.hs     #0x207aeb8
0207adcc: add      x8, x25, x23
0207add0: stp      s0, s1, [x8, #0x20]
0207add4: str      s2, [x8, #0x28]
0207add8: ldr      x0, [x19, #0x88]
0207addc: add      x23, x23, #0xc
0207ade0: add      x22, x22, #1
0207ade4: cbnz     x0, #0x207ada0
0207ade8: b        #0x207aeb4
0207adec: ldp      w0, w1, [x19, #0xa0]
0207adf0: mov      x2, xzr
0207adf4: bl       #0x390b0d8 ; UnityEngine.Random$$Range
0207adf8: ldr      x8, [x21]
0207adfc: mov      w1, w0
0207ae00: mov      x0, x8
0207ae04: bl       #0x18ddc6c
0207ae08: mov      x21, x19
0207ae0c: str      x0, [x21, #0x78]!
0207ae10: mov      x1, x0
0207ae14: mov      x0, x21
0207ae18: bl       #0x18ddb68
0207ae1c: ldr      x22, [x21]
0207ae20: cbz      x22, #0x207aeb4
0207ae24: mov      x24, xzr
0207ae28: mov      x23, xzr
0207ae2c: ldrsw    x8, [x22, #0x18]
0207ae30: cmp      x23, x8
0207ae34: b.ge     #0x207ae6c
0207ae38: mov      x0, x19
0207ae3c: bl       #0x207b2d8 ; FishFlock.FishGroup$$RandomPos
0207ae40: ldr      w8, [x22, #0x18]
0207ae44: cmp      x23, x8
0207ae48: b.hs     #0x207aeb8
0207ae4c: add      x8, x22, x24
0207ae50: stp      s0, s1, [x8, #0x20]
0207ae54: str      s2, [x8, #0x28]
0207ae58: ldr      x22, [x21]
0207ae5c: add      x24, x24, #0xc
0207ae60: add      x23, x23, #1
0207ae64: cbnz     x22, #0x207ae2c
0207ae68: b        #0x207aeb4
0207ae6c: tbz      w20, #0, #0x207ae78
0207ae70: mov      w8, wzr
0207ae74: b        #0x207ae9c
0207ae78: ldr      x8, [x19, #0x78]
0207ae7c: cbz      x8, #0x207aeb4
0207ae80: ldr      w8, [x8, #0x18]
0207ae84: ldr      w9, [x19, #0x90]
0207ae88: sub      w8, w8, #1
0207ae8c: cmp      w9, w8
0207ae90: csel     w8, w8, w9, gt
0207ae94: cmp      w9, #0
0207ae98: csel     w8, wzr, w8, lt
0207ae9c: str      w8, [x19, #0x90]
0207aea0: ldp      x20, x19, [sp, #0x30]
0207aea4: ldp      x22, x21, [sp, #0x20]
0207aea8: ldp      x24, x23, [sp, #0x10]
0207aeac: ldp      x30, x25, [sp], #0x40
0207aeb0: ret
0207aeb4: bl       #0x18dde20
0207aeb8: bl       #0x18dde28

; 0x207b448 FishFlock.FishGroup$$SetGroupPosition | void SetGroupPosition(Vector3 at)
0207b448: sub      sp, sp, #0x110
0207b44c: str      d10, [sp, #0xb0]
0207b450: stp      d9, d8, [sp, #0xc0]
0207b454: stp      x30, x25, [sp, #0xd0]
0207b458: stp      x24, x23, [sp, #0xe0]
0207b45c: stp      x22, x21, [sp, #0xf0]
0207b460: stp      x20, x19, [sp, #0x100]
0207b464: mrs      x21, tpidr_el0
0207b468: ldr      x8, [x21, #0x28]
0207b46c: adrp     x20, #0x3ed5000
0207b470: mov      v8.16b, v2.16b
0207b474: mov      v9.16b, v1.16b
0207b478: str      x8, [sp, #0xa8]
0207b47c: ldrb     w8, [x20, #0x4d6]
0207b480: mov      v10.16b, v0.16b
0207b484: mov      x19, x0
0207b488: tbnz     w8, #0, #0x207b4b8
0207b48c: adrp     x0, #0x3c2c000
0207b490: ldr      x0, [x0, #0x710]
0207b494: bl       #0x18ddbc4
0207b498: adrp     x0, #0x3c2c000
0207b49c: ldr      x0, [x0, #0x718]
0207b4a0: bl       #0x18ddbc4
0207b4a4: adrp     x0, #0x3c2c000
0207b4a8: ldr      x0, [x0, #0x720]
0207b4ac: bl       #0x18ddbc4
0207b4b0: mov      w8, #1
0207b4b4: strb     w8, [x20, #0x4d6]
0207b4b8: ldr      x0, [x19, #0x60]
0207b4bc: stp      s10, s9, [x19, #0x94]
0207b4c0: str      s8, [x19, #0x9c]
0207b4c4: cbz      x0, #0x207b588
0207b4c8: adrp     x23, #0x3c2c000
0207b4cc: adrp     x24, #0x3c2c000
0207b4d0: ldr      x23, [x23, #0x718]
0207b4d4: ldr      x24, [x24, #0x720]
0207b4d8: add      x8, sp, #8
0207b4dc: mov      w20, wzr
0207b4e0: add      x22, sp, #0x70
0207b4e4: add      x25, x8, #0xc
0207b4e8: ldr      w8, [x0, #0x18]
0207b4ec: cmp      w20, w8
0207b4f0: b.ge     #0x207b58c
0207b4f4: ldr      x2, [x23]
0207b4f8: add      x8, sp, #8
0207b4fc: mov      w1, w20
0207b500: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207b504: ldur     q0, [x25, #0x1c]
0207b508: ldp      q2, q1, [x25]
0207b50c: mov      x0, xzr
0207b510: stur     q0, [x22, #0x1c]
0207b514: stp      q2, q1, [sp, #0x70]
0207b518: ldur     d8, [x19, #0x94]
0207b51c: ldr      s9, [x19, #0x9c]
0207b520: bl       #0x390b188 ; UnityEngine.Random$$get_insideUnitSphere
0207b524: ldr      x0, [x19, #0x60]
0207b528: ldp      q4, q5, [sp, #0x70]
0207b52c: ldur     q6, [x22, #0x1c]
0207b530: ldr      s3, [x19, #0x3c]
0207b534: stp      q4, q5, [sp, #0x40]
0207b538: stur     q6, [sp, #0x5c]
0207b53c: cbz      x0, #0x207b588
0207b540: mov      v0.s[1], v1.s[0]
0207b544: ldr      x3, [x24]
0207b548: ldp      q1, q4, [sp, #0x40]
0207b54c: ldur     q5, [sp, #0x5c]
0207b550: fmul     s2, s2, s3
0207b554: fmul     v0.2s, v0.2s, v3.s[0]
0207b558: fadd     s2, s9, s2
0207b55c: fadd     v0.2s, v8.2s, v0.2s
0207b560: add      x2, sp, #8
0207b564: mov      w1, w20
0207b568: str      s2, [sp, #0x10]
0207b56c: str      d0, [sp, #8]
0207b570: stur     q5, [x25, #0x1c]
0207b574: stp      q1, q4, [x25]
0207b578: bl       #0x27fbfd4 ; System.Collections.Generic.List<FishData>$$set_Item
0207b57c: ldr      x0, [x19, #0x60]
0207b580: add      w20, w20, #1
0207b584: cbnz     x0, #0x207b4e8
0207b588: bl       #0x18dde20
0207b58c: ldr      x8, [x21, #0x28]
0207b590: ldr      x9, [sp, #0xa8]
0207b594: cmp      x8, x9
0207b598: b.ne     #0x207b5bc
0207b59c: ldp      x20, x19, [sp, #0x100]
0207b5a0: ldp      x22, x21, [sp, #0xf0]
0207b5a4: ldp      x24, x23, [sp, #0xe0]
0207b5a8: ldp      x30, x25, [sp, #0xd0]
0207b5ac: ldp      d9, d8, [sp, #0xc0]
0207b5b0: ldr      d10, [sp, #0xb0]
0207b5b4: add      sp, sp, #0x110
0207b5b8: ret
0207b5bc: bl       #0x3a16ae0 ; __stack_chk_fail

; 0x207b2d8 FishFlock.FishGroup$$RandomPos | Vector3 RandomPos()
0207b2d8: stp      d15, d14, [sp, #-0x60]!
0207b2dc: stp      d13, d12, [sp, #0x10]
0207b2e0: stp      d11, d10, [sp, #0x20]
0207b2e4: stp      d9, d8, [sp, #0x30]
0207b2e8: str      x30, [sp, #0x40]
0207b2ec: stp      x20, x19, [sp, #0x50]
0207b2f0: mov      x19, x0
0207b2f4: ldr      x0, [x0, #0xa8]
0207b2f8: cbz      x0, #0x207b444
0207b2fc: mov      x1, xzr
0207b300: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207b304: cbz      x0, #0x207b444
0207b308: mov      x1, xzr
0207b30c: mov      x20, x0
0207b310: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207b314: ldr      x8, [x19, #0xa8]
0207b318: cbz      x8, #0x207b444
0207b31c: ldr      s14, [x8, #0x20]
0207b320: mov      x0, x20
0207b324: mov      x1, xzr
0207b328: mov      v8.16b, v0.16b
0207b32c: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207b330: ldr      x8, [x19, #0xa8]
0207b334: cbz      x8, #0x207b444
0207b338: ldr      s10, [x8, #0x20]
0207b33c: mov      x0, x20
0207b340: mov      x1, xzr
0207b344: mov      v9.16b, v0.16b
0207b348: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207b34c: ldr      x8, [x19, #0xa8]
0207b350: cbz      x8, #0x207b444
0207b354: ldr      s11, [x8, #0x24]
0207b358: mov      x0, x20
0207b35c: mov      x1, xzr
0207b360: mov      v12.16b, v1.16b
0207b364: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207b368: ldr      x8, [x19, #0xa8]
0207b36c: cbz      x8, #0x207b444
0207b370: stp      s12, s8, [sp, #0x48]
0207b374: ldr      s8, [x8, #0x24]
0207b378: mov      x0, x20
0207b37c: mov      x1, xzr
0207b380: mov      v15.16b, v1.16b
0207b384: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207b388: ldr      x8, [x19, #0xa8]
0207b38c: cbz      x8, #0x207b444
0207b390: ldr      s13, [x8, #0x28]
0207b394: mov      x0, x20
0207b398: mov      x1, xzr
0207b39c: mov      v12.16b, v2.16b
0207b3a0: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207b3a4: ldr      x8, [x19, #0xa8]
0207b3a8: cbz      x8, #0x207b444
0207b3ac: fmov     s3, #0.50000000
0207b3b0: fmul     s0, s13, s3
0207b3b4: fsub     s12, s12, s0
0207b3b8: ldr      s0, [sp, #0x48]
0207b3bc: fmul     s5, s11, s3
0207b3c0: ldr      s4, [x8, #0x28]
0207b3c4: fmul     s6, s10, s3
0207b3c8: fsub     s10, s0, s5
0207b3cc: ldr      s5, [sp, #0x4c]
0207b3d0: fmul     s1, s8, s3
0207b3d4: fmul     s0, s14, s3
0207b3d8: fadd     s11, s15, s1
0207b3dc: fadd     s1, s9, s6
0207b3e0: fsub     s0, s5, s0
0207b3e4: fmul     s3, s4, s3
0207b3e8: mov      x0, xzr
0207b3ec: fadd     s8, s2, s3
0207b3f0: bl       #0x390b098 ; UnityEngine.Random$$Range
0207b3f4: mov      v9.16b, v0.16b
0207b3f8: mov      v0.16b, v10.16b
0207b3fc: mov      v1.16b, v11.16b
0207b400: mov      x0, xzr
0207b404: bl       #0x390b098 ; UnityEngine.Random$$Range
0207b408: mov      v10.16b, v0.16b
0207b40c: mov      v0.16b, v12.16b
0207b410: mov      v1.16b, v8.16b
0207b414: mov      x0, xzr
0207b418: bl       #0x390b098 ; UnityEngine.Random$$Range
0207b41c: mov      v2.16b, v0.16b
0207b420: mov      v0.16b, v9.16b
0207b424: mov      v1.16b, v10.16b
0207b428: ldp      x20, x19, [sp, #0x50]
0207b42c: ldr      x30, [sp, #0x40]
0207b430: ldp      d9, d8, [sp, #0x30]
0207b434: ldp      d11, d10, [sp, #0x20]
0207b438: ldp      d13, d12, [sp, #0x10]
0207b43c: ldp      d15, d14, [sp], #0x60
0207b440: ret
0207b444: bl       #0x18dde20

; 0x207b5c0 FishFlock.FishGroup$$OnDrawGizmos | void OnDrawGizmos()
0207b5c0: sub      sp, sp, #0x80
0207b5c4: str      d8, [sp, #0x40]
0207b5c8: str      x30, [sp, #0x48]
0207b5cc: stp      x24, x23, [sp, #0x50]
0207b5d0: stp      x22, x21, [sp, #0x60]
0207b5d4: stp      x20, x19, [sp, #0x70]
0207b5d8: adrp     x20, #0x3ed5000
0207b5dc: ldrb     w8, [x20, #0x4d7]
0207b5e0: mov      x19, x0
0207b5e4: tbnz     w8, #0, #0x207b608
0207b5e8: adrp     x0, #0x3c2c000
0207b5ec: ldr      x0, [x0, #0x710]
0207b5f0: bl       #0x18ddbc4
0207b5f4: adrp     x0, #0x3c2c000
0207b5f8: ldr      x0, [x0, #0x718]
0207b5fc: bl       #0x18ddbc4
0207b600: mov      w8, #1
0207b604: strb     w8, [x20, #0x4d7]
0207b608: ldrb     w8, [x19, #0x24]
0207b60c: cbz      w8, #0x207b6e4
0207b610: ldrb     w8, [x19, #0x54]
0207b614: cbz      w8, #0x207b700
0207b618: fmov     s0, #1.00000000
0207b61c: fmov     s1, wzr
0207b620: fmov     s2, wzr
0207b624: fmov     s3, #1.00000000
0207b628: mov      x0, xzr
0207b62c: bl       #0x38d8254 ; UnityEngine.Gizmos$$set_color
0207b630: adrp     x8, #0x980000
0207b634: ldr      s8, [x8, #0x8b0]
0207b638: ldp      s0, s1, [x19, #0x94]
0207b63c: ldr      s2, [x19, #0x9c]
0207b640: mov      x0, xzr
0207b644: mov      v3.16b, v8.16b
0207b648: bl       #0x38d7e50 ; UnityEngine.Gizmos$$DrawWireSphere
0207b64c: fmov     s0, #0.50000000
0207b650: fmov     s1, #0.50000000
0207b654: fmov     s2, #0.50000000
0207b658: fmov     s3, #1.00000000
0207b65c: mov      x0, xzr
0207b660: bl       #0x38d8254 ; UnityEngine.Gizmos$$set_color
0207b664: ldr      x0, [x19, #0x60]
0207b668: cbz      x0, #0x207b7c4
0207b66c: adrp     x21, #0x3c2c000
0207b670: ldr      x21, [x21, #0x718]
0207b674: mov      w20, wzr
0207b678: ldr      w8, [x0, #0x18]
0207b67c: cmp      w20, w8
0207b680: b.ge     #0x207b6b8
0207b684: ldr      x2, [x21]
0207b688: add      x8, sp, #8
0207b68c: mov      w1, w20
0207b690: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207b694: ldp      s0, s1, [sp, #8]
0207b698: ldr      s2, [sp, #0x10]
0207b69c: ldr      s3, [x19, #0x40]
0207b6a0: mov      x0, xzr
0207b6a4: bl       #0x38d7e50 ; UnityEngine.Gizmos$$DrawWireSphere
0207b6a8: ldr      x0, [x19, #0x60]
0207b6ac: add      w20, w20, #1
0207b6b0: cbnz     x0, #0x207b678
0207b6b4: b        #0x207b7c4
0207b6b8: fmov     s0, wzr
0207b6bc: fmov     s1, wzr
0207b6c0: fmov     s2, #1.00000000
0207b6c4: fmov     s3, #1.00000000
0207b6c8: mov      x0, xzr
0207b6cc: bl       #0x38d8254 ; UnityEngine.Gizmos$$set_color
0207b6d0: mov      x0, x19
0207b6d4: bl       #0x207b7cc ; FishFlock.FishGroup$$CalculateCenterPoint
0207b6d8: mov      v3.16b, v8.16b
0207b6dc: mov      x0, xzr
0207b6e0: bl       #0x38d7e50 ; UnityEngine.Gizmos$$DrawWireSphere
0207b6e4: ldp      x20, x19, [sp, #0x70]
0207b6e8: ldp      x22, x21, [sp, #0x60]
0207b6ec: ldp      x24, x23, [sp, #0x50]
0207b6f0: ldr      x30, [sp, #0x48]
0207b6f4: ldr      d8, [sp, #0x40]
0207b6f8: add      sp, sp, #0x80
0207b6fc: ret
0207b700: fmov     s0, wzr
0207b704: fmov     s1, #1.00000000
0207b708: fmov     s2, wzr
0207b70c: fmov     s3, #1.00000000
0207b710: mov      x0, xzr
0207b714: bl       #0x38d8254 ; UnityEngine.Gizmos$$set_color
0207b718: ldr      x8, [x19, #0x78]
0207b71c: cbz      x8, #0x207b7c4
0207b720: mov      x20, xzr
0207b724: mov      x21, xzr
0207b728: mov      x22, #0x100000000
0207b72c: mov      w23, #0xc
0207b730: mov      x24, #0x100000000
0207b734: ldr      w9, [x8, #0x18]
0207b738: cmp      x21, w9, sxtw
0207b73c: b.ge     #0x207b618
0207b740: sub      w10, w9, #1
0207b744: cmp      x21, w10, sxtw
0207b748: b.ge     #0x207b78c
0207b74c: cmp      x21, x9
0207b750: b.hs     #0x207b7c8
0207b754: add      x10, x21, #1
0207b758: cmp      x10, x9
0207b75c: b.hs     #0x207b7c8
0207b760: asr      x9, x24, #0x20
0207b764: add      x10, x8, x20
0207b768: madd     x8, x9, x23, x8
0207b76c: ldp      s1, s2, [x10, #0x24]
0207b770: ldr      s0, [x10, #0x20]
0207b774: ldp      s3, s4, [x8, #0x20]
0207b778: ldr      s5, [x8, #0x28]
0207b77c: mov      x0, xzr
0207b780: bl       #0x38d7dbc ; UnityEngine.Gizmos$$DrawLine
0207b784: ldr      x8, [x19, #0x78]
0207b788: cbz      x8, #0x207b7c4
0207b78c: ldr      w9, [x8, #0x18]
0207b790: cmp      x21, x9
0207b794: b.hs     #0x207b7c8
0207b798: add      x8, x8, x20
0207b79c: ldp      s0, s1, [x8, #0x20]
0207b7a0: ldr      s2, [x8, #0x28]
0207b7a4: fmov     s3, #1.00000000
0207b7a8: mov      x0, xzr
0207b7ac: bl       #0x38d7e50 ; UnityEngine.Gizmos$$DrawWireSphere
0207b7b0: ldr      x8, [x19, #0x78]
0207b7b4: add      x21, x21, #1
0207b7b8: add      x20, x20, #0xc
0207b7bc: add      x24, x24, x22
0207b7c0: cbnz     x8, #0x207b734
0207b7c4: bl       #0x18dde20
0207b7c8: bl       #0x18dde28

; 0x207b9ac FishFlock.FishGroup$$OnUpdate | void OnUpdate()
0207b9ac: sub      sp, sp, #0x120
0207b9b0: str      d12, [sp, #0x90]
0207b9b4: stp      d11, d10, [sp, #0xa0]
0207b9b8: stp      d9, d8, [sp, #0xb0]
0207b9bc: stp      x29, x30, [sp, #0xc0]
0207b9c0: stp      x28, x27, [sp, #0xd0]
0207b9c4: stp      x26, x25, [sp, #0xe0]
0207b9c8: stp      x24, x23, [sp, #0xf0]
0207b9cc: stp      x22, x21, [sp, #0x100]
0207b9d0: stp      x20, x19, [sp, #0x110]
0207b9d4: adrp     x20, #0x3ed5000
0207b9d8: ldrb     w8, [x20, #0x4d8]
0207b9dc: mov      x19, x0
0207b9e0: tbnz     w8, #0, #0x207ba10
0207b9e4: adrp     x0, #0x3c2c000
0207b9e8: ldr      x0, [x0, #0x710]
0207b9ec: bl       #0x18ddbc4
0207b9f0: adrp     x0, #0x3c2c000
0207b9f4: ldr      x0, [x0, #0x718]
0207b9f8: bl       #0x18ddbc4
0207b9fc: adrp     x0, #0x3c2c000
0207ba00: ldr      x0, [x0, #0x720]
0207ba04: bl       #0x18ddbc4
0207ba08: mov      w8, #1
0207ba0c: strb     w8, [x20, #0x4d8]
0207ba10: ldr      x0, [x19, #0x60]
0207ba14: cbz      x0, #0x207bc04
0207ba18: adrp     x23, #0x3c2c000
0207ba1c: adrp     x24, #0x3c2c000
0207ba20: adrp     x9, #0x980000
0207ba24: adrp     x21, #0x3bf7000
0207ba28: ldr      x23, [x23, #0x718]
0207ba2c: ldr      x24, [x24, #0x720]
0207ba30: ldr      s11, [x9, #0x590]
0207ba34: ldr      x21, [x21, #0x380]
0207ba38: add      x8, sp, #0x58
0207ba3c: mov      w20, wzr
0207ba40: adrp     x25, #0x3ed1000
0207ba44: add      x26, x8, #0x18
0207ba48: add      x27, x8, #0x29
0207ba4c: adrp     x29, #0x3ed1000
0207ba50: ldr      w8, [x0, #0x18]
0207ba54: cmp      w20, w8
0207ba58: b.ge     #0x207bc08
0207ba5c: ldr      x2, [x23]
0207ba60: add      x8, sp, #0x58
0207ba64: mov      w1, w20
0207ba68: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207ba6c: ldr      s8, [sp, #0x58]
0207ba70: ldur     d1, [sp, #0x5c]
0207ba74: ldr      s10, [sp, #0x64]
0207ba78: ldr      d9, [sp, #0x68]
0207ba7c: ldr      q0, [x26]
0207ba80: ldrb     w28, [sp, #0x80]
0207ba84: ldur     w8, [x27, #3]
0207ba88: ldr      w9, [x27]
0207ba8c: ldr      x22, [sp, #0x88]
0207ba90: str      q0, [sp, #0x40]
0207ba94: stur     w8, [sp, #0x9b]
0207ba98: str      w9, [sp, #0x98]
0207ba9c: tbz      w28, #0, #0x207bb74
0207baa0: ldrb     w8, [x19, #0x25]
0207baa4: cbz      w8, #0x207bb74
0207baa8: cbz      x22, #0x207bc04
0207baac: mov      s2, v1.s[1]
0207bab0: mov      x0, x22
0207bab4: mov      v0.16b, v8.16b
0207bab8: mov      x1, xzr
0207babc: str      q1, [sp, #0x10]
0207bac0: bl       #0x391b0b0 ; UnityEngine.Transform$$set_position
0207bac4: ldrb     w8, [x25, #0x995]
0207bac8: cbnz     w8, #0x207badc
0207bacc: mov      x0, x21
0207bad0: bl       #0x18ddbc4
0207bad4: mov      w8, #1
0207bad8: strb     w8, [x25, #0x995]
0207badc: ldr      x8, [x21]
0207bae0: ldr      q1, [sp, #0x10]
0207bae4: fadd     s0, s8, s10
0207bae8: fsub     s8, s0, s8
0207baec: ldr      x8, [x8, #0xb8]
0207baf0: fadd     v2.2s, v1.2s, v9.2s
0207baf4: fsub     v1.2s, v2.2s, v1.2s
0207baf8: ldr      s0, [x8]
0207bafc: ldur     d3, [x8, #4]
0207bb00: fsub     s0, s8, s0
0207bb04: fsub     v2.2s, v1.2s, v3.2s
0207bb08: fmul     s0, s0, s0
0207bb0c: fmul     v2.2s, v2.2s, v2.2s
0207bb10: fadd     s0, s0, s2
0207bb14: mov      s2, v2.s[1]
0207bb18: fadd     s0, s2, s0
0207bb1c: fcmp     s0, s11
0207bb20: b.mi     #0x207bbf8
0207bb24: ldrb     w9, [x29, #0x87d]
0207bb28: cbnz     w9, #0x207bb4c
0207bb2c: mov      x0, x21
0207bb30: str      q1, [sp, #0x10]
0207bb34: bl       #0x18ddbc4
0207bb38: ldr      x8, [x21]
0207bb3c: mov      w9, #1
0207bb40: strb     w9, [x29, #0x87d]
0207bb44: ldr      q1, [sp, #0x10]
0207bb48: ldr      x8, [x8, #0xb8]
0207bb4c: ldp      s3, s4, [x8, #0x18]
0207bb50: ldr      s5, [x8, #0x20]
0207bb54: mov      s2, v1.s[1]
0207bb58: mov      v0.16b, v8.16b
0207bb5c: mov      x0, xzr
0207bb60: bl       #0x3905848 ; UnityEngine.Quaternion$$LookRotation
0207bb64: mov      x0, x22
0207bb68: mov      x1, xzr
0207bb6c: bl       #0x391b27c ; UnityEngine.Transform$$set_rotation
0207bb70: b        #0x207bbf8
0207bb74: cbz      x22, #0x207bc04
0207bb78: mov      x0, x22
0207bb7c: mov      x1, xzr
0207bb80: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207bb84: mov      x0, x22
0207bb88: mov      x1, xzr
0207bb8c: mov      v8.16b, v0.16b
0207bb90: mov      v9.16b, v1.16b
0207bb94: mov      v10.16b, v2.16b
0207bb98: bl       #0x391b5c0 ; UnityEngine.Transform$$get_forward
0207bb9c: ldr      x0, [x19, #0x60]
0207bba0: ldr      q3, [sp, #0x40]
0207bba4: ldr      w8, [sp, #0x98]
0207bba8: ldur     w9, [sp, #0x9b]
0207bbac: str      q3, [sp, #0x30]
0207bbb0: str      w8, [sp, #0x28]
0207bbb4: stur     w9, [sp, #0x2b]
0207bbb8: cbz      x0, #0x207bc04
0207bbbc: ldr      x3, [x24]
0207bbc0: stp      s10, s0, [sp, #0x60]
0207bbc4: ldr      q0, [sp, #0x30]
0207bbc8: ldur     w8, [sp, #0x2b]
0207bbcc: ldr      w9, [sp, #0x28]
0207bbd0: add      x2, sp, #0x58
0207bbd4: mov      w1, w20
0207bbd8: stp      s8, s9, [sp, #0x58]
0207bbdc: stp      s1, s2, [sp, #0x68]
0207bbe0: str      q0, [x26]
0207bbe4: strb     w28, [sp, #0x80]
0207bbe8: stur     w8, [x27, #3]
0207bbec: str      w9, [x27]
0207bbf0: str      x22, [sp, #0x88]
0207bbf4: bl       #0x27fbfd4 ; System.Collections.Generic.List<FishData>$$set_Item
0207bbf8: ldr      x0, [x19, #0x60]
0207bbfc: add      w20, w20, #1
0207bc00: cbnz     x0, #0x207ba50
0207bc04: bl       #0x18dde20
0207bc08: ldp      s8, s9, [x19, #0x44]
0207bc0c: fcmp     s9, s8
0207bc10: str      s8, [x19, #0x4c]
0207bc14: b.eq     #0x207bc70
0207bc18: mov      x0, xzr
0207bc1c: bl       #0x391903c ; UnityEngine.Time$$get_smoothDeltaTime
0207bc20: ldr      s10, [x19, #0x50]
0207bc24: fmov     s11, #1.00000000
0207bc28: fmov     s12, wzr
0207bc2c: mov      x0, xzr
0207bc30: fdiv     s0, s0, s10
0207bc34: fmin     s1, s0, s11
0207bc38: fcmp     s0, #0.0
0207bc3c: fcsel    s0, s1, s12, pl
0207bc40: fsub     s1, s8, s9
0207bc44: fmul     s0, s1, s0
0207bc48: fadd     s0, s9, s0
0207bc4c: str      s0, [x19, #0x48]
0207bc50: bl       #0x391903c ; UnityEngine.Time$$get_smoothDeltaTime
0207bc54: fmin     s1, s0, s11
0207bc58: fcmp     s0, #0.0
0207bc5c: fcsel    s0, s1, s12, pl
0207bc60: fsub     s1, s11, s10
0207bc64: fmul     s0, s1, s0
0207bc68: fadd     s0, s10, s0
0207bc6c: str      s0, [x19, #0x50]
0207bc70: ldp      x20, x19, [sp, #0x110]
0207bc74: ldp      x22, x21, [sp, #0x100]
0207bc78: ldp      x24, x23, [sp, #0xf0]
0207bc7c: ldp      x26, x25, [sp, #0xe0]
0207bc80: ldp      x28, x27, [sp, #0xd0]
0207bc84: ldp      x29, x30, [sp, #0xc0]
0207bc88: ldp      d9, d8, [sp, #0xb0]
0207bc8c: ldp      d11, d10, [sp, #0xa0]
0207bc90: ldr      d12, [sp, #0x90]
0207bc94: add      sp, sp, #0x120
0207bc98: ret

; 0x207bc9c FishFlock.FishGroup$$CreateBehaviour | FishData CreateBehaviour(float scale)
0207bc9c: sub      sp, sp, #0x80
0207bca0: stp      d15, d14, [sp, #0x20]
0207bca4: stp      d13, d12, [sp, #0x30]
0207bca8: stp      d11, d10, [sp, #0x40]
0207bcac: stp      d9, d8, [sp, #0x50]
0207bcb0: str      x30, [sp, #0x60]
0207bcb4: stp      x20, x19, [sp, #0x70]
0207bcb8: stp      xzr, xzr, [sp, #0x10]
0207bcbc: ldp      s9, s10, [x0, #0x94]
0207bcc0: ldr      s12, [x0, #0x9c]
0207bcc4: mov      x20, x0
0207bcc8: mov      x0, xzr
0207bccc: mov      v8.16b, v0.16b
0207bcd0: mov      x19, x8
0207bcd4: bl       #0x390b188 ; UnityEngine.Random$$get_insideUnitSphere
0207bcd8: ldr      x0, [x20, #0xa8]
0207bcdc: cbz      x0, #0x207be34
0207bce0: stp      s0, s8, [sp, #0x68]
0207bce4: ldr      s8, [x20, #0x3c]
0207bce8: mov      x1, xzr
0207bcec: mov      v11.16b, v2.16b
0207bcf0: mov      v15.16b, v1.16b
0207bcf4: str      s9, [sp, #0xc]
0207bcf8: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207bcfc: cbz      x0, #0x207be34
0207bd00: fmul     s0, s11, s8
0207bd04: mov      x1, xzr
0207bd08: fadd     s9, s12, s0
0207bd0c: bl       #0x391b1f8 ; UnityEngine.Transform$$get_rotation
0207bd10: mov      x0, xzr
0207bd14: mov      v11.16b, v0.16b
0207bd18: mov      v12.16b, v1.16b
0207bd1c: mov      v13.16b, v2.16b
0207bd20: mov      v14.16b, v3.16b
0207bd24: bl       #0x390b210 ; UnityEngine.Random$$get_rotation
0207bd28: mov      w8, #0x999a
0207bd2c: mov      v4.16b, v0.16b
0207bd30: mov      v5.16b, v1.16b
0207bd34: mov      v6.16b, v2.16b
0207bd38: mov      v7.16b, v3.16b
0207bd3c: movk     w8, #0x3e99, lsl #16
0207bd40: mov      v0.16b, v11.16b
0207bd44: mov      v1.16b, v12.16b
0207bd48: mov      v2.16b, v13.16b
0207bd4c: mov      v3.16b, v14.16b
0207bd50: mov      x0, xzr
0207bd54: str      w8, [sp]
0207bd58: bl       #0x3905330 ; UnityEngine.Quaternion$$Slerp
0207bd5c: ldr      w8, [x20, #0x20]
0207bd60: cmp      w8, #2
0207bd64: b.eq     #0x207bd84
0207bd68: fmul     s4, s15, s8
0207bd6c: cmp      w8, #1
0207bd70: fadd     s13, s10, s4
0207bd74: b.ne     #0x207bd8c
0207bd78: fmov     s2, wzr
0207bd7c: fmov     s15, wzr
0207bd80: b        #0x207bd90
0207bd84: fmov     s1, wzr
0207bd88: fmov     s13, wzr
0207bd8c: mov      v15.16b, v9.16b
0207bd90: ldr      s4, [sp, #0x68]
0207bd94: ldr      s5, [sp, #0xc]
0207bd98: mov      x0, xzr
0207bd9c: fmul     s4, s4, s8
0207bda0: fadd     s8, s5, s4
0207bda4: bl       #0x3905644 ; UnityEngine.Quaternion$$Internal_ToEulerRad
0207bda8: adrp     x8, #0x980000
0207bdac: ldr      s3, [x8, #0x968]
0207bdb0: mov      x0, xzr
0207bdb4: fmul     s0, s0, s3
0207bdb8: fmul     s1, s1, s3
0207bdbc: fmul     s2, s2, s3
0207bdc0: bl       #0x3905c5c ; UnityEngine.Quaternion$$Internal_MakePositive
0207bdc4: mov      v9.16b, v0.16b
0207bdc8: mov      v10.16b, v1.16b
0207bdcc: ldp      s0, s1, [x20, #0x28]
0207bdd0: mov      x0, xzr
0207bdd4: mov      v11.16b, v2.16b
0207bdd8: bl       #0x390b098 ; UnityEngine.Random$$Range
0207bddc: ldp      s2, s1, [x20, #0x30]
0207bde0: mov      v12.16b, v0.16b
0207bde4: mov      x0, xzr
0207bde8: mov      v0.16b, v2.16b
0207bdec: bl       #0x390b098 ; UnityEngine.Random$$Range
0207bdf0: ldr      q1, [sp, #0x10]
0207bdf4: stp      s12, s0, [x19, #0x18]
0207bdf8: ldr      s0, [sp, #0x6c]
0207bdfc: stp      s8, s13, [x19]
0207be00: stp      s15, s9, [x19, #8]
0207be04: stp      s10, s11, [x19, #0x10]
0207be08: str      wzr, [x19, #0x20]
0207be0c: str      s0, [x19, #0x24]
0207be10: stur     q1, [x19, #0x28]
0207be14: ldp      x20, x19, [sp, #0x70]
0207be18: ldr      x30, [sp, #0x60]
0207be1c: ldp      d9, d8, [sp, #0x50]
0207be20: ldp      d11, d10, [sp, #0x40]
0207be24: ldp      d13, d12, [sp, #0x30]
0207be28: ldp      d15, d14, [sp, #0x20]
0207be2c: add      sp, sp, #0x80
0207be30: ret
0207be34: bl       #0x18dde20

; 0x207be38 FishFlock.FishGroup$$AddFish | FishData AddFish(GameObject fishPrefab, float scale)
0207be38: sub      sp, sp, #0x80
0207be3c: str      d8, [sp, #0x40]
0207be40: stp      x30, x23, [sp, #0x50]
0207be44: stp      x22, x21, [sp, #0x60]
0207be48: stp      x20, x19, [sp, #0x70]
0207be4c: adrp     x23, #0x3ed5000
0207be50: adrp     x22, #0x3bf7000
0207be54: mov      x19, x8
0207be58: ldrb     w8, [x23, #0x4d9]
0207be5c: ldr      x22, [x22, #0x468]
0207be60: mov      v8.16b, v0.16b
0207be64: mov      x21, x1
0207be68: mov      x20, x0
0207be6c: tbnz     w8, #0, #0x207be90
0207be70: adrp     x0, #0x3c27000
0207be74: ldr      x0, [x0, #0xf10]
0207be78: bl       #0x18ddbc4
0207be7c: adrp     x0, #0x3bf7000
0207be80: ldr      x0, [x0, #0x468]
0207be84: bl       #0x18ddbc4
0207be88: mov      w8, #1
0207be8c: strb     w8, [x23, #0x4d9]
0207be90: ldr      x0, [x22]
0207be94: ldr      w8, [x0, #0xe0]
0207be98: cbnz     w8, #0x207bea0
0207be9c: bl       #0x18ddcfc
0207bea0: mov      x0, x21
0207bea4: mov      x1, xzr
0207bea8: mov      x2, xzr
0207beac: bl       #0x39106d8 ; UnityEngine.Object$$op_Equality
0207beb0: tbz      w0, #0, #0x207bec8
0207beb4: movi     v0.2d, #0000000000000000
0207beb8: str      xzr, [x19, #0x30]
0207bebc: stp      q0, q0, [x19, #0x10]
0207bec0: str      q0, [x19]
0207bec4: b        #0x207bf40
0207bec8: mov      x0, x20
0207becc: mov      x1, xzr
0207bed0: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207bed4: ldr      x8, [x22]
0207bed8: mov      x22, x0
0207bedc: ldr      w9, [x8, #0xe0]
0207bee0: cbnz     w9, #0x207beec
0207bee4: mov      x0, x8
0207bee8: bl       #0x18ddcfc
0207beec: adrp     x8, #0x3c27000
0207bef0: ldr      x8, [x8, #0xf10]
0207bef4: mov      x0, x21
0207bef8: mov      x1, x22
0207befc: ldr      x2, [x8]
0207bf00: bl       #0x22f20ac ; UnityEngine.Object$$Instantiate<object>
0207bf04: cbz      x0, #0x207bf58
0207bf08: mov      x1, xzr
0207bf0c: bl       #0x390f5d8 ; UnityEngine.GameObject$$get_transform
0207bf10: mov      x1, x0
0207bf14: add      x8, sp, #8
0207bf18: mov      x0, x20
0207bf1c: mov      v0.16b, v8.16b
0207bf20: bl       #0x207bf5c ; FishFlock.FishGroup$$AddFish
0207bf24: ldr      x8, [sp, #0x38]
0207bf28: ldur     q0, [sp, #0x28]
0207bf2c: ldur     q1, [sp, #0x18]
0207bf30: ldur     q2, [sp, #8]
0207bf34: str      x8, [x19, #0x30]
0207bf38: stp      q1, q0, [x19, #0x10]
0207bf3c: str      q2, [x19]
0207bf40: ldp      x20, x19, [sp, #0x70]
0207bf44: ldp      x22, x21, [sp, #0x60]
0207bf48: ldp      x30, x23, [sp, #0x50]
0207bf4c: ldr      d8, [sp, #0x40]
0207bf50: add      sp, sp, #0x80
0207bf54: ret
0207bf58: bl       #0x18dde20

; 0x207bf5c FishFlock.FishGroup$$AddFish | FishData AddFish(Transform fishTransform, float scale)
0207bf5c: sub      sp, sp, #0x180
0207bf60: stp      d15, d14, [sp, #0x110]
0207bf64: stp      d13, d12, [sp, #0x120]
0207bf68: stp      d11, d10, [sp, #0x130]
0207bf6c: stp      d9, d8, [sp, #0x140]
0207bf70: stp      x29, x30, [sp, #0x150]
0207bf74: stp      x22, x21, [sp, #0x160]
0207bf78: stp      x20, x19, [sp, #0x170]
0207bf7c: adrp     x22, #0x3ed5000
0207bf80: ldrb     w9, [x22, #0x4da]
0207bf84: mov      v8.16b, v0.16b
0207bf88: mov      x21, x1
0207bf8c: mov      x20, x0
0207bf90: mov      x19, x8
0207bf94: tbnz     w9, #0, #0x207bfac
0207bf98: adrp     x0, #0x3c2c000
0207bf9c: ldr      x0, [x0, #0x748]
0207bfa0: bl       #0x18ddbc4
0207bfa4: mov      w8, #1
0207bfa8: strb     w8, [x22, #0x4da]
0207bfac: movi     v0.2d, #0000000000000000
0207bfb0: stp      q0, q0, [sp, #0x60]
0207bfb4: str      q0, [sp, #0x50]
0207bfb8: add      x8, sp, #0x50
0207bfbc: mov      x0, x20
0207bfc0: mov      v0.16b, v8.16b
0207bfc4: str      xzr, [sp, #0x80]
0207bfc8: bl       #0x207bc9c ; FishFlock.FishGroup$$CreateBehaviour
0207bfcc: ldp      s12, s11, [x20, #0x94]
0207bfd0: ldr      s13, [x20, #0x9c]
0207bfd4: mov      x0, xzr
0207bfd8: bl       #0x390b188 ; UnityEngine.Random$$get_insideUnitSphere
0207bfdc: ldr      x0, [x20, #0xa8]
0207bfe0: cbz      x0, #0x207c2f8
0207bfe4: stp      s1, s8, [sp, #8]
0207bfe8: ldr      s8, [x20, #0x3c]
0207bfec: mov      x1, xzr
0207bff0: mov      v9.16b, v0.16b
0207bff4: mov      v10.16b, v2.16b
0207bff8: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207bffc: cbz      x0, #0x207c2f8
0207c000: fmul     s0, s9, s8
0207c004: fmul     s1, s10, s8
0207c008: mov      x1, xzr
0207c00c: fadd     s9, s12, s0
0207c010: fadd     s10, s13, s1
0207c014: bl       #0x391b1f8 ; UnityEngine.Transform$$get_rotation
0207c018: mov      x0, xzr
0207c01c: mov      v12.16b, v0.16b
0207c020: mov      v13.16b, v1.16b
0207c024: mov      v14.16b, v2.16b
0207c028: mov      v15.16b, v3.16b
0207c02c: bl       #0x390b210 ; UnityEngine.Random$$get_rotation
0207c030: mov      w8, #0x999a
0207c034: mov      v4.16b, v0.16b
0207c038: mov      v5.16b, v1.16b
0207c03c: mov      v6.16b, v2.16b
0207c040: mov      v7.16b, v3.16b
0207c044: movk     w8, #0x3e99, lsl #16
0207c048: mov      v0.16b, v12.16b
0207c04c: mov      v1.16b, v13.16b
0207c050: mov      v2.16b, v14.16b
0207c054: mov      v3.16b, v15.16b
0207c058: mov      x0, xzr
0207c05c: str      w8, [sp]
0207c060: bl       #0x3905330 ; UnityEngine.Quaternion$$Slerp
0207c064: ldr      w8, [x20, #0x20]
0207c068: cmp      w8, #2
0207c06c: b.eq     #0x207c094
0207c070: ldr      s4, [sp, #8]
0207c074: cmp      w8, #1
0207c078: fmul     s4, s4, s8
0207c07c: ldr      s8, [sp, #0xc]
0207c080: fadd     s11, s11, s4
0207c084: b.ne     #0x207c0a0
0207c088: fmov     s2, wzr
0207c08c: fmov     s10, wzr
0207c090: b        #0x207c0a0
0207c094: ldr      s8, [sp, #0xc]
0207c098: fmov     s1, wzr
0207c09c: fmov     s11, wzr
0207c0a0: mov      x0, xzr
0207c0a4: stp      s9, s11, [sp, #0x50]
0207c0a8: str      s10, [sp, #0x58]
0207c0ac: bl       #0x3905644 ; UnityEngine.Quaternion$$Internal_ToEulerRad
0207c0b0: adrp     x8, #0x980000
0207c0b4: ldr      s3, [x8, #0x968]
0207c0b8: mov      x0, xzr
0207c0bc: fmul     s0, s0, s3
0207c0c0: fmul     s1, s1, s3
0207c0c4: fmul     s2, s2, s3
0207c0c8: bl       #0x3905c5c ; UnityEngine.Quaternion$$Internal_MakePositive
0207c0cc: stp      s0, s1, [sp, #0x5c]
0207c0d0: str      s2, [sp, #0x64]
0207c0d4: ldp      s0, s1, [x20, #0x28]
0207c0d8: mov      x0, xzr
0207c0dc: bl       #0x390b098 ; UnityEngine.Random$$Range
0207c0e0: str      s0, [sp, #0x68]
0207c0e4: ldp      s0, s1, [x20, #0x30]
0207c0e8: mov      x0, xzr
0207c0ec: bl       #0x390b098 ; UnityEngine.Random$$Range
0207c0f0: mov      w8, #1
0207c0f4: mov      x0, x20
0207c0f8: mov      x1, xzr
0207c0fc: str      s0, [sp, #0x6c]
0207c100: str      s8, [sp, #0x74]
0207c104: strb     w8, [sp, #0x78]
0207c108: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207c10c: cbz      x21, #0x207c2f8
0207c110: mov      x1, x0
0207c114: mov      x0, x21
0207c118: mov      x2, xzr
0207c11c: bl       #0x391ba24 ; UnityEngine.Transform$$SetParent
0207c120: adrp     x22, #0x3ed1000
0207c124: ldrb     w8, [x22, #0x98f]
0207c128: cbnz     w8, #0x207c140
0207c12c: adrp     x0, #0x3bf7000
0207c130: ldr      x0, [x0, #0xe10]
0207c134: bl       #0x18ddbc4
0207c138: mov      w8, #1
0207c13c: strb     w8, [x22, #0x98f]
0207c140: adrp     x8, #0x3bf7000
0207c144: ldr      x8, [x8, #0xe10]
0207c148: mov      x0, x21
0207c14c: mov      v0.16b, v9.16b
0207c150: mov      v1.16b, v11.16b
0207c154: ldr      x8, [x8]
0207c158: mov      v2.16b, v10.16b
0207c15c: mov      x1, xzr
0207c160: ldr      x8, [x8, #0xb8]
0207c164: ldp      s3, s4, [x8]
0207c168: ldp      s5, s6, [x8, #8]
0207c16c: bl       #0x391bbb4 ; UnityEngine.Transform$$SetPositionAndRotation
0207c170: add      x8, sp, #0x50
0207c174: add      x0, x8, #0x30
0207c178: mov      x1, x21
0207c17c: str      x21, [sp, #0x80]
0207c180: bl       #0x18ddb68
0207c184: mov      x0, xzr
0207c188: bl       #0x390b160 ; UnityEngine.Random$$get_value
0207c18c: adrp     x22, #0x3ed3000
0207c190: ldr      x21, [sp, #0x80]
0207c194: ldrb     w8, [x22, #0x933]
0207c198: ldr      s8, [sp, #0x74]
0207c19c: fmov     s1, #10.00000000
0207c1a0: fmul     s0, s0, s1
0207c1a4: str      s0, [sp, #0x70]
0207c1a8: cbnz     w8, #0x207c1c0
0207c1ac: adrp     x0, #0x3bf7000
0207c1b0: ldr      x0, [x0, #0x380]
0207c1b4: bl       #0x18ddbc4
0207c1b8: mov      w8, #1
0207c1bc: strb     w8, [x22, #0x933]
0207c1c0: cbz      x21, #0x207c2f8
0207c1c4: adrp     x8, #0x3bf7000
0207c1c8: ldr      x8, [x8, #0x380]
0207c1cc: mov      x0, x21
0207c1d0: mov      x1, xzr
0207c1d4: ldr      x8, [x8]
0207c1d8: ldr      x8, [x8, #0xb8]
0207c1dc: ldp      s1, s0, [x8, #0x10]
0207c1e0: ldr      s3, [x8, #0xc]
0207c1e4: fmul     s2, s8, s0
0207c1e8: fmul     s1, s8, s1
0207c1ec: fmul     s0, s8, s3
0207c1f0: bl       #0x391b800 ; UnityEngine.Transform$$set_localScale
0207c1f4: ldr      x0, [x20, #0x60]
0207c1f8: ldp      q0, q1, [sp, #0x50]
0207c1fc: ldr      q2, [sp, #0x70]
0207c200: ldr      x8, [sp, #0x80]
0207c204: stp      q0, q1, [sp, #0x10]
0207c208: str      q2, [sp, #0x30]
0207c20c: str      x8, [sp, #0x40]
0207c210: cbz      x0, #0x207c2f8
0207c214: adrp     x9, #0x3c2c000
0207c218: ldr      x9, [x9, #0x748]
0207c21c: ldp      q0, q1, [sp, #0x10]
0207c220: ldr      q2, [sp, #0x30]
0207c224: ldr      x8, [sp, #0x40]
0207c228: ldr      x10, [x9]
0207c22c: stp      q0, q1, [sp, #0x90]
0207c230: str      q2, [sp, #0xb0]
0207c234: str      x8, [sp, #0xc0]
0207c238: ldr      w11, [x0, #0x1c]
0207c23c: ldr      x8, [x0, #0x10]
0207c240: add      w9, w11, #1
0207c244: str      w9, [x0, #0x1c]
0207c248: cbz      x8, #0x207c2f8
0207c24c: ldrsw    x9, [x0, #0x18]
0207c250: ldr      w11, [x8, #0x18]
0207c254: cmp      w9, w11
0207c258: b.hs     #0x207c290
0207c25c: add      w10, w9, #1
0207c260: str      w10, [x0, #0x18]
0207c264: ldr      x10, [sp, #0xc0]
0207c268: ldp      q2, q0, [sp, #0xa0]
0207c26c: ldr      q1, [sp, #0x90]
0207c270: mov      w11, #0x38
0207c274: madd     x0, x9, x11, x8
0207c278: str      x10, [x0, #0x50]!
0207c27c: mov      x1, xzr
0207c280: stp      q2, q0, [x0, #-0x20]
0207c284: stur     q1, [x0, #-0x30]
0207c288: bl       #0x18ddb68
0207c28c: b        #0x207c2bc
0207c290: ldr      x8, [x10, #0x20]
0207c294: ldp      q0, q1, [sp, #0x90]
0207c298: ldr      q2, [sp, #0xb0]
0207c29c: ldr      x9, [sp, #0xc0]
0207c2a0: ldr      x8, [x8, #0xc0]
0207c2a4: add      x1, sp, #0xd0
0207c2a8: ldr      x2, [x8, #0x70]
0207c2ac: stp      q0, q1, [sp, #0xd0]
0207c2b0: str      q2, [sp, #0xf0]
0207c2b4: str      x9, [sp, #0x100]
0207c2b8: bl       #0x27fc364 ; System.Collections.Generic.List<FishData>$$AddWithResize
0207c2bc: ldr      x8, [sp, #0x80]
0207c2c0: ldp      q1, q0, [sp, #0x60]
0207c2c4: ldr      q2, [sp, #0x50]
0207c2c8: ldp      x22, x21, [sp, #0x160]
0207c2cc: str      x8, [x19, #0x30]
0207c2d0: stp      q1, q0, [x19, #0x10]
0207c2d4: str      q2, [x19]
0207c2d8: ldp      x20, x19, [sp, #0x170]
0207c2dc: ldp      x29, x30, [sp, #0x150]
0207c2e0: ldp      d9, d8, [sp, #0x140]
0207c2e4: ldp      d11, d10, [sp, #0x130]
0207c2e8: ldp      d13, d12, [sp, #0x120]
0207c2ec: ldp      d15, d14, [sp, #0x110]
0207c2f0: add      sp, sp, #0x180
0207c2f4: ret
0207c2f8: bl       #0x18dde20

; 0x207c2fc FishFlock.FishGroup$$OnValidate | void OnValidate()
0207c2fc: b        #0x207c300 ; FishFlock.FishGroup$$ResetSpeed

; 0x207c300 FishFlock.FishGroup$$ResetSpeed | void ResetSpeed()
0207c300: sub      sp, sp, #0x100
0207c304: str      d8, [sp, #0xc0]
0207c308: stp      x30, x23, [sp, #0xd0]
0207c30c: stp      x22, x21, [sp, #0xe0]
0207c310: stp      x20, x19, [sp, #0xf0]
0207c314: adrp     x20, #0x3ed5000
0207c318: ldrb     w8, [x20, #0x4db]
0207c31c: mov      x19, x0
0207c320: tbnz     w8, #0, #0x207c350
0207c324: adrp     x0, #0x3c2c000
0207c328: ldr      x0, [x0, #0x710]
0207c32c: bl       #0x18ddbc4
0207c330: adrp     x0, #0x3c2c000
0207c334: ldr      x0, [x0, #0x718]
0207c338: bl       #0x18ddbc4
0207c33c: adrp     x0, #0x3c2c000
0207c340: ldr      x0, [x0, #0x720]
0207c344: bl       #0x18ddbc4
0207c348: mov      w8, #1
0207c34c: strb     w8, [x20, #0x4db]
0207c350: ldr      x0, [x19, #0x60]
0207c354: cbz      x0, #0x207c438
0207c358: adrp     x21, #0x3c2c000
0207c35c: adrp     x22, #0x3c2c000
0207c360: ldr      x21, [x21, #0x718]
0207c364: ldr      x22, [x22, #0x720]
0207c368: add      x8, sp, #0x80
0207c36c: mov      w20, wzr
0207c370: add      x23, x8, #0x20
0207c374: ldr      w8, [x0, #0x18]
0207c378: cmp      w20, w8
0207c37c: b.ge     #0x207c43c
0207c380: ldr      x2, [x21]
0207c384: add      x8, sp, #0x80
0207c388: mov      w1, w20
0207c38c: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207c390: ldr      q0, [sp, #0x80]
0207c394: ldr      x8, [sp, #0x90]
0207c398: ldr      q1, [x23]
0207c39c: ldr      x9, [x23, #0x10]
0207c3a0: str      q0, [sp, #0x60]
0207c3a4: str      x8, [sp, #0x70]
0207c3a8: str      q1, [sp, #0x40]
0207c3ac: str      x9, [sp, #0x50]
0207c3b0: ldp      s0, s1, [x19, #0x28]
0207c3b4: mov      x0, xzr
0207c3b8: bl       #0x390b098 ; UnityEngine.Random$$Range
0207c3bc: ldp      s2, s1, [x19, #0x30]
0207c3c0: mov      v8.16b, v0.16b
0207c3c4: mov      x0, xzr
0207c3c8: mov      v0.16b, v2.16b
0207c3cc: bl       #0x390b098 ; UnityEngine.Random$$Range
0207c3d0: ldr      x0, [x19, #0x60]
0207c3d4: ldr      q1, [sp, #0x60]
0207c3d8: ldr      x8, [sp, #0x70]
0207c3dc: ldr      q2, [sp, #0x40]
0207c3e0: ldr      x9, [sp, #0x50]
0207c3e4: str      q1, [sp, #0x20]
0207c3e8: str      x8, [sp, #0x30]
0207c3ec: str      q2, [sp]
0207c3f0: str      x9, [sp, #0x10]
0207c3f4: cbz      x0, #0x207c438
0207c3f8: ldr      x3, [x22]
0207c3fc: ldr      q1, [sp, #0x20]
0207c400: ldr      x8, [sp, #0x30]
0207c404: stp      s8, s0, [sp, #0x98]
0207c408: ldr      x9, [sp, #0x10]
0207c40c: ldr      q0, [sp]
0207c410: add      x2, sp, #0x80
0207c414: mov      w1, w20
0207c418: str      q1, [sp, #0x80]
0207c41c: str      x8, [sp, #0x90]
0207c420: str      x9, [x23, #0x10]
0207c424: str      q0, [x23]
0207c428: bl       #0x27fbfd4 ; System.Collections.Generic.List<FishData>$$set_Item
0207c42c: ldr      x0, [x19, #0x60]
0207c430: add      w20, w20, #1
0207c434: cbnz     x0, #0x207c374
0207c438: bl       #0x18dde20
0207c43c: ldp      x20, x19, [sp, #0xf0]
0207c440: ldp      x22, x21, [sp, #0xe0]
0207c444: ldp      x30, x23, [sp, #0xd0]
0207c448: ldr      d8, [sp, #0xc0]
0207c44c: add      sp, sp, #0x100
0207c450: ret

; 0x207c454 FishFlock.FishGroup$$SetScale | void SetScale(Transform fishTransform, float scale)
0207c454: str      d8, [sp, #-0x20]!
0207c458: stp      x30, x19, [sp, #0x10]
0207c45c: mov      v8.16b, v0.16b
0207c460: mov      x19, x0
0207c464: bl       #0x207c480 ; FishFlock.FishGroup$$FindFishIndexByTransform
0207c468: mov      w1, w0
0207c46c: mov      x0, x19
0207c470: ldp      x30, x19, [sp, #0x10]
0207c474: mov      v0.16b, v8.16b
0207c478: ldr      d8, [sp], #0x20
0207c47c: b        #0x207c548 ; FishFlock.FishGroup$$SetScale

; 0x207c548 FishFlock.FishGroup$$SetScale | void SetScale(int index, float scale)
0207c548: sub      sp, sp, #0x70
0207c54c: str      d8, [sp, #0x40]
0207c550: stp      x30, x21, [sp, #0x50]
0207c554: stp      x20, x19, [sp, #0x60]
0207c558: adrp     x21, #0x3ed5000
0207c55c: ldrb     w8, [x21, #0x4dc]
0207c560: mov      v8.16b, v0.16b
0207c564: mov      w19, w1
0207c568: mov      x20, x0
0207c56c: tbnz     w8, #0, #0x207c590
0207c570: adrp     x0, #0x3c2c000
0207c574: ldr      x0, [x0, #0x710]
0207c578: bl       #0x18ddbc4
0207c57c: adrp     x0, #0x3c2c000
0207c580: ldr      x0, [x0, #0x718]
0207c584: bl       #0x18ddbc4
0207c588: mov      w8, #1
0207c58c: strb     w8, [x21, #0x4dc]
0207c590: tbnz     w19, #0x1f, #0x207c618
0207c594: ldr      x0, [x20, #0x60]
0207c598: cbz      x0, #0x207c62c
0207c59c: ldr      w8, [x0, #0x18]
0207c5a0: cmp      w8, w19
0207c5a4: b.le     #0x207c618
0207c5a8: adrp     x8, #0x3c2c000
0207c5ac: ldr      x8, [x8, #0x718]
0207c5b0: mov      w1, w19
0207c5b4: ldr      x2, [x8]
0207c5b8: add      x8, sp, #8
0207c5bc: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207c5c0: adrp     x20, #0x3ed3000
0207c5c4: ldrb     w8, [x20, #0x933]
0207c5c8: ldr      x19, [sp, #0x38]
0207c5cc: cbnz     w8, #0x207c5e4
0207c5d0: adrp     x0, #0x3bf7000
0207c5d4: ldr      x0, [x0, #0x380]
0207c5d8: bl       #0x18ddbc4
0207c5dc: mov      w8, #1
0207c5e0: strb     w8, [x20, #0x933]
0207c5e4: cbz      x19, #0x207c62c
0207c5e8: adrp     x8, #0x3bf7000
0207c5ec: ldr      x8, [x8, #0x380]
0207c5f0: mov      x0, x19
0207c5f4: mov      x1, xzr
0207c5f8: ldr      x8, [x8]
0207c5fc: ldr      x8, [x8, #0xb8]
0207c600: ldp      s1, s0, [x8, #0x10]
0207c604: ldr      s3, [x8, #0xc]
0207c608: fmul     s2, s0, s8
0207c60c: fmul     s1, s1, s8
0207c610: fmul     s0, s3, s8
0207c614: bl       #0x391b800 ; UnityEngine.Transform$$set_localScale
0207c618: ldp      x20, x19, [sp, #0x60]
0207c61c: ldp      x30, x21, [sp, #0x50]
0207c620: ldr      d8, [sp, #0x40]
0207c624: add      sp, sp, #0x70
0207c628: ret
0207c62c: bl       #0x18dde20

; 0x207c630 FishFlock.FishGroup$$RemoveFish | bool RemoveFish(int index = 0)
0207c630: sub      sp, sp, #0x60
0207c634: stp      x30, x21, [sp, #0x40]
0207c638: stp      x20, x19, [sp, #0x50]
0207c63c: adrp     x21, #0x3ed5000
0207c640: ldrb     w8, [x21, #0x4dd]
0207c644: mov      w19, w1
0207c648: mov      x20, x0
0207c64c: tbnz     w8, #0, #0x207c688
0207c650: adrp     x0, #0x3c2c000
0207c654: ldr      x0, [x0, #0x750]
0207c658: bl       #0x18ddbc4
0207c65c: adrp     x0, #0x3c2c000
0207c660: ldr      x0, [x0, #0x710]
0207c664: bl       #0x18ddbc4
0207c668: adrp     x0, #0x3c2c000
0207c66c: ldr      x0, [x0, #0x718]
0207c670: bl       #0x18ddbc4
0207c674: adrp     x0, #0x3bf7000
0207c678: ldr      x0, [x0, #0x468]
0207c67c: bl       #0x18ddbc4
0207c680: mov      w8, #1
0207c684: strb     w8, [x21, #0x4dd]
0207c688: tbnz     w19, #0x1f, #0x207c718
0207c68c: ldr      x0, [x20, #0x60]
0207c690: cbz      x0, #0x207c72c
0207c694: ldr      w8, [x0, #0x18]
0207c698: cmp      w8, w19
0207c69c: b.le     #0x207c718
0207c6a0: adrp     x8, #0x3c2c000
0207c6a4: ldr      x8, [x8, #0x718]
0207c6a8: mov      w1, w19
0207c6ac: ldr      x2, [x8]
0207c6b0: add      x8, sp, #8
0207c6b4: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207c6b8: ldr      x0, [sp, #0x38]
0207c6bc: cbz      x0, #0x207c72c
0207c6c0: mov      x1, xzr
0207c6c4: bl       #0x390dab8 ; UnityEngine.Component$$get_gameObject
0207c6c8: adrp     x8, #0x3bf7000
0207c6cc: ldr      x8, [x8, #0x468]
0207c6d0: mov      x21, x0
0207c6d4: ldr      x8, [x8]
0207c6d8: ldr      w9, [x8, #0xe0]
0207c6dc: cbnz     w9, #0x207c6e8
0207c6e0: mov      x0, x8
0207c6e4: bl       #0x18ddcfc
0207c6e8: mov      x0, x21
0207c6ec: mov      x1, xzr
0207c6f0: bl       #0x3914160 ; UnityEngine.Object$$Destroy
0207c6f4: ldr      x0, [x20, #0x60]
0207c6f8: cbz      x0, #0x207c72c
0207c6fc: adrp     x8, #0x3c2c000
0207c700: ldr      x8, [x8, #0x750]
0207c704: mov      w1, w19
0207c708: ldr      x2, [x8]
0207c70c: bl       #0x27fe5e8 ; System.Collections.Generic.List<FishData>$$RemoveAt
0207c710: mov      w0, #1
0207c714: b        #0x207c71c
0207c718: mov      w0, wzr
0207c71c: ldp      x20, x19, [sp, #0x50]
0207c720: ldp      x30, x21, [sp, #0x40]
0207c724: add      sp, sp, #0x60
0207c728: ret
0207c72c: bl       #0x18dde20

; 0x207c730 FishFlock.FishGroup$$RemoveFish | bool RemoveFish(Transform fishTransform)
0207c730: stp      x30, x19, [sp, #-0x10]!
0207c734: mov      x19, x0
0207c738: bl       #0x207c480 ; FishFlock.FishGroup$$FindFishIndexByTransform
0207c73c: mov      w1, w0
0207c740: mov      x0, x19
0207c744: ldp      x30, x19, [sp], #0x10
0207c748: b        #0x207c630 ; FishFlock.FishGroup$$RemoveFish

; 0x207c480 FishFlock.FishGroup$$FindFishIndexByTransform | int FindFishIndexByTransform(Transform fishTransform)
0207c480: sub      sp, sp, #0x70
0207c484: str      x30, [sp, #0x40]
0207c488: stp      x22, x21, [sp, #0x50]
0207c48c: stp      x20, x19, [sp, #0x60]
0207c490: adrp     x21, #0x3ed5000
0207c494: ldrb     w8, [x21, #0x4de]
0207c498: mov      x19, x1
0207c49c: mov      x20, x0
0207c4a0: tbnz     w8, #0, #0x207c4c4
0207c4a4: adrp     x0, #0x3c2c000
0207c4a8: ldr      x0, [x0, #0x710]
0207c4ac: bl       #0x18ddbc4
0207c4b0: adrp     x0, #0x3c2c000
0207c4b4: ldr      x0, [x0, #0x718]
0207c4b8: bl       #0x18ddbc4
0207c4bc: mov      w8, #1
0207c4c0: strb     w8, [x21, #0x4de]
0207c4c4: ldr      x0, [x20, #0x60]
0207c4c8: cbz      x0, #0x207c544
0207c4cc: ldr      w8, [x0, #0x18]
0207c4d0: cmp      w8, #1
0207c4d4: b.lt     #0x207c528
0207c4d8: adrp     x22, #0x3c2c000
0207c4dc: ldr      x22, [x22, #0x718]
0207c4e0: mov      w21, wzr
0207c4e4: ldr      x2, [x22]
0207c4e8: add      x8, sp, #8
0207c4ec: mov      w1, w21
0207c4f0: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207c4f4: cbz      x19, #0x207c544
0207c4f8: ldr      x8, [x19]
0207c4fc: ldr      x1, [sp, #0x38]
0207c500: mov      x0, x19
0207c504: ldp      x9, x2, [x8, #0x138]
0207c508: blr      x9
0207c50c: tbnz     w0, #0, #0x207c52c
0207c510: ldr      x0, [x20, #0x60]
0207c514: cbz      x0, #0x207c544
0207c518: ldr      w8, [x0, #0x18]
0207c51c: add      w21, w21, #1
0207c520: cmp      w21, w8
0207c524: b.lt     #0x207c4e4
0207c528: mov      w21, #-1
0207c52c: mov      w0, w21
0207c530: ldp      x20, x19, [sp, #0x60]
0207c534: ldp      x22, x21, [sp, #0x50]
0207c538: ldr      x30, [sp, #0x40]
0207c53c: add      sp, sp, #0x70
0207c540: ret
0207c544: bl       #0x18dde20

; 0x207c74c FishFlock.FishGroup$$GetFishCount | int GetFishCount()
0207c74c: str      x30, [sp, #-0x20]!
0207c750: stp      x20, x19, [sp, #0x10]
0207c754: adrp     x20, #0x3ed5000
0207c758: ldrb     w8, [x20, #0x4df]
0207c75c: mov      x19, x0
0207c760: tbnz     w8, #0, #0x207c778
0207c764: adrp     x0, #0x3c2c000
0207c768: ldr      x0, [x0, #0x710]
0207c76c: bl       #0x18ddbc4
0207c770: mov      w8, #1
0207c774: strb     w8, [x20, #0x4df]
0207c778: ldr      x8, [x19, #0x60]
0207c77c: cbz      x8, #0x207c790
0207c780: ldr      w0, [x8, #0x18]
0207c784: ldp      x20, x19, [sp, #0x10]
0207c788: ldr      x30, [sp], #0x20
0207c78c: ret
0207c790: bl       #0x18dde20

; 0x207c794 FishFlock.FishGroup$$AddPrePosition | void AddPrePosition(Vector3 pos)
0207c794: str      d10, [sp, #-0x30]!
0207c798: stp      d9, d8, [sp, #8]
0207c79c: str      x30, [sp, #0x18]
0207c7a0: stp      x20, x19, [sp, #0x20]
0207c7a4: adrp     x20, #0x3ed5000
0207c7a8: ldrb     w8, [x20, #0x4e0]
0207c7ac: mov      v8.16b, v2.16b
0207c7b0: mov      v9.16b, v1.16b
0207c7b4: mov      v10.16b, v0.16b
0207c7b8: mov      x19, x0
0207c7bc: tbnz     w8, #0, #0x207c7d4
0207c7c0: adrp     x0, #0x3c1c000
0207c7c4: ldr      x0, [x0, #0xd30]
0207c7c8: bl       #0x18ddbc4
0207c7cc: mov      w8, #1
0207c7d0: strb     w8, [x20, #0x4e0]
0207c7d4: ldr      x0, [x19, #0x88]
0207c7d8: cbz      x0, #0x207c864
0207c7dc: adrp     x9, #0x3c1c000
0207c7e0: ldr      x9, [x9, #0xd30]
0207c7e4: ldr      w10, [x0, #0x1c]
0207c7e8: ldr      x8, [x0, #0x10]
0207c7ec: ldr      x9, [x9]
0207c7f0: add      w10, w10, #1
0207c7f4: str      w10, [x0, #0x1c]
0207c7f8: cbz      x8, #0x207c864
0207c7fc: ldrsw    x10, [x0, #0x18]
0207c800: ldr      w11, [x8, #0x18]
0207c804: cmp      w10, w11
0207c808: b.hs     #0x207c838
0207c80c: mov      w11, #0xc
0207c810: add      w9, w10, #1
0207c814: madd     x8, x10, x11, x8
0207c818: str      w9, [x0, #0x18]
0207c81c: stp      s10, s9, [x8, #0x20]
0207c820: str      s8, [x8, #0x28]
0207c824: ldp      x20, x19, [sp, #0x20]
0207c828: ldr      x30, [sp, #0x18]
0207c82c: ldp      d9, d8, [sp, #8]
0207c830: ldr      d10, [sp], #0x30
0207c834: ret
0207c838: ldr      x8, [x9, #0x20]
0207c83c: mov      v1.16b, v9.16b
0207c840: mov      v2.16b, v8.16b
0207c844: ldp      x20, x19, [sp, #0x20]
0207c848: ldr      x8, [x8, #0xc0]
0207c84c: ldr      x30, [sp, #0x18]
0207c850: ldp      d9, d8, [sp, #8]
0207c854: mov      v0.16b, v10.16b
0207c858: ldr      x1, [x8, #0x70]
0207c85c: ldr      d10, [sp], #0x30
0207c860: b        #0x2871e68 ; System.Collections.Generic.List<Vector3>$$AddWithResize
0207c864: bl       #0x18dde20

; 0x207b7cc FishFlock.FishGroup$$CalculateCenterPoint | Vector3 CalculateCenterPoint()
0207b7cc: sub      sp, sp, #0xe0
0207b7d0: str      d8, [sp, #0xb0]
0207b7d4: stp      x30, x21, [sp, #0xc0]
0207b7d8: stp      x20, x19, [sp, #0xd0]
0207b7dc: adrp     x20, #0x3ed5000
0207b7e0: ldrb     w8, [x20, #0x4e1]
0207b7e4: mov      x19, x0
0207b7e8: tbnz     w8, #0, #0x207b830
0207b7ec: adrp     x0, #0x3c2c000
0207b7f0: ldr      x0, [x0, #0x728]
0207b7f4: bl       #0x18ddbc4
0207b7f8: adrp     x0, #0x3c2c000
0207b7fc: ldr      x0, [x0, #0x730]
0207b800: bl       #0x18ddbc4
0207b804: adrp     x0, #0x3c2c000
0207b808: ldr      x0, [x0, #0x738]
0207b80c: bl       #0x18ddbc4
0207b810: adrp     x0, #0x3c2c000
0207b814: ldr      x0, [x0, #0x740]
0207b818: bl       #0x18ddbc4
0207b81c: adrp     x0, #0x3c2c000
0207b820: ldr      x0, [x0, #0x710]
0207b824: bl       #0x18ddbc4
0207b828: mov      w8, #1
0207b82c: strb     w8, [x20, #0x4e1]
0207b830: adrp     x20, #0x3ed1000
0207b834: ldrb     w8, [x20, #0x995]
0207b838: movi     v0.2d, #0000000000000000
0207b83c: str      xzr, [sp, #0xa0]
0207b840: stp      q0, q0, [sp, #0x80]
0207b844: stp      q0, q0, [sp, #0x60]
0207b848: cbnz     w8, #0x207b860
0207b84c: adrp     x0, #0x3bf7000
0207b850: ldr      x0, [x0, #0x380]
0207b854: bl       #0x18ddbc4
0207b858: mov      w8, #1
0207b85c: strb     w8, [x20, #0x995]
0207b860: ldr      x0, [x19, #0x60]
0207b864: cbz      x0, #0x207b934
0207b868: adrp     x8, #0x3bf7000
0207b86c: ldr      x8, [x8, #0x380]
0207b870: ldr      w21, [x0, #0x18]
0207b874: ldr      x8, [x8]
0207b878: cmp      w21, #1
0207b87c: ldr      x8, [x8, #0xb8]
0207b880: ldr      d0, [x8]
0207b884: ldr      s8, [x8, #8]
0207b888: str      q0, [sp]
0207b88c: b.lt     #0x207b914
0207b890: adrp     x8, #0x3c2c000
0207b894: ldr      x8, [x8, #0x740]
0207b898: adrp     x20, #0x3c2c000
0207b89c: adrp     x19, #0x3c2c000
0207b8a0: ldr      x1, [x8]
0207b8a4: ldr      x20, [x20, #0x730]
0207b8a8: ldr      x19, [x19, #0x728]
0207b8ac: add      x8, sp, #0x18
0207b8b0: bl       #0x27fd39c ; System.Collections.Generic.List<FishData>$$GetEnumerator
0207b8b4: add      x0, sp, #0x60
0207b8b8: add      x1, sp, #0x18
0207b8bc: mov      w2, #0x48
0207b8c0: bl       #0x3a16aa0 ; memcpy
0207b8c4: ldr      x1, [x20]
0207b8c8: add      x0, sp, #0x60
0207b8cc: bl       #0x25f2b20 ; System.Collections.Generic.List.Enumerator<FishData>$$MoveNext
0207b8d0: tbz      w0, #0, #0x207b8f0
0207b8d4: ldr      d0, [sp, #0x70]
0207b8d8: ldr      s1, [sp, #0x78]
0207b8dc: ldr      q2, [sp]
0207b8e0: fadd     s8, s8, s1
0207b8e4: fadd     v2.2s, v2.2s, v0.2s
0207b8e8: str      q2, [sp]
0207b8ec: b        #0x207b8c4
0207b8f0: ldr      x1, [x19]
0207b8f4: add      x0, sp, #0x60
0207b8f8: bl       #0x25f2b1c ; System.Collections.Generic.List.Enumerator<FishData>$$Dispose
0207b8fc: ldr      q0, [sp]
0207b900: scvtf    s2, w21
0207b904: dup      v1.2s, v2.s[0]
0207b908: fdiv     s8, s8, s2
0207b90c: fdiv     v0.2s, v0.2s, v1.2s
0207b910: b        #0x207b918
0207b914: ldr      q0, [sp]
0207b918: mov      v2.16b, v8.16b
0207b91c: ldp      x20, x19, [sp, #0xd0]
0207b920: ldp      x30, x21, [sp, #0xc0]
0207b924: ldr      d8, [sp, #0xb0]
0207b928: mov      s1, v0.s[1]
0207b92c: add      sp, sp, #0xe0
0207b930: ret
0207b934: bl       #0x18dde20
0207b938: cmp      w1, #1
0207b93c: mov      x20, x0
0207b940: b.ne     #0x207b974
0207b944: mov      x0, x20
0207b948: bl       #0x3a16a60 ; __cxa_begin_catch
0207b94c: ldr      x19, [x0]
0207b950: bl       #0x3a16a70 ; __cxa_end_catch
0207b954: adrp     x8, #0x3c2c000
0207b958: ldr      x8, [x8, #0x728]
0207b95c: add      x0, sp, #0x60
0207b960: ldr      x1, [x8]
0207b964: bl       #0x25f2b1c ; System.Collections.Generic.List.Enumerator<FishData>$$Dispose
0207b968: cbz      x19, #0x207b8fc
0207b96c: mov      x0, x19
0207b970: bl       #0x18dde18
0207b974: mov      x19, xzr
0207b978: b        #0x207b980
0207b97c: mov      x20, x0
0207b980: adrp     x8, #0x3c2c000
0207b984: ldr      x8, [x8, #0x728]
0207b988: ldr      x1, [x8]
0207b98c: add      x0, sp, #0x60
0207b990: bl       #0x25f2b1c ; System.Collections.Generic.List.Enumerator<FishData>$$Dispose
0207b994: cbnz     x19, #0x207b9a0
0207b998: mov      x0, x20
0207b99c: bl       #0x198e98c
0207b9a0: mov      x0, x19
0207b9a4: bl       #0x18dde18
0207b9a8: bl       #0x15e191c

; 0x207c868 FishFlock.FishGroup$$UpdateFishDataByTransform | void UpdateFishDataByTransform(FishData fishData)
0207c868: sub      sp, sp, #0xb0
0207c86c: str      x30, [sp, #0x80]
0207c870: stp      x22, x21, [sp, #0x90]
0207c874: stp      x20, x19, [sp, #0xa0]
0207c878: adrp     x21, #0x3ed5000
0207c87c: ldrb     w8, [x21, #0x4e2]
0207c880: mov      x19, x1
0207c884: mov      x20, x0
0207c888: tbnz     w8, #0, #0x207c8b8
0207c88c: adrp     x0, #0x3c2c000
0207c890: ldr      x0, [x0, #0x710]
0207c894: bl       #0x18ddbc4
0207c898: adrp     x0, #0x3c2c000
0207c89c: ldr      x0, [x0, #0x718]
0207c8a0: bl       #0x18ddbc4
0207c8a4: adrp     x0, #0x3c2c000
0207c8a8: ldr      x0, [x0, #0x720]
0207c8ac: bl       #0x18ddbc4
0207c8b0: mov      w8, #1
0207c8b4: strb     w8, [x21, #0x4e2]
0207c8b8: ldr      x0, [x20, #0x60]
0207c8bc: cbz      x0, #0x207c978
0207c8c0: adrp     x22, #0x3c2c000
0207c8c4: ldr      x22, [x22, #0x718]
0207c8c8: mov      w21, wzr
0207c8cc: ldr      w8, [x0, #0x18]
0207c8d0: cmp      w21, w8
0207c8d4: b.ge     #0x207c964
0207c8d8: ldr      x2, [x22]
0207c8dc: add      x8, sp, #0x40
0207c8e0: mov      w1, w21
0207c8e4: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207c8e8: ldr      x0, [sp, #0x70]
0207c8ec: cbz      x0, #0x207c978
0207c8f0: ldr      x8, [x0]
0207c8f4: ldr      x1, [x19, #0x30]
0207c8f8: ldp      x9, x2, [x8, #0x138]
0207c8fc: blr      x9
0207c900: tbnz     w0, #0, #0x207c914
0207c904: ldr      x0, [x20, #0x60]
0207c908: add      w21, w21, #1
0207c90c: cbnz     x0, #0x207c8cc
0207c910: b        #0x207c978
0207c914: ldp      q2, q0, [x19, #0x10]
0207c918: ldr      x8, [x19, #0x30]
0207c91c: ldr      q1, [x19]
0207c920: ldr      x0, [x20, #0x60]
0207c924: stp      q2, q0, [sp, #0x10]
0207c928: str      x8, [sp, #0x30]
0207c92c: str      q1, [sp]
0207c930: cbz      x0, #0x207c978
0207c934: adrp     x8, #0x3c2c000
0207c938: ldr      x8, [x8, #0x720]
0207c93c: ldp      q0, q1, [sp]
0207c940: ldr      q2, [sp, #0x20]
0207c944: ldr      x9, [sp, #0x30]
0207c948: ldr      x3, [x8]
0207c94c: add      x2, sp, #0x40
0207c950: mov      w1, w21
0207c954: stp      q0, q1, [sp, #0x40]
0207c958: str      q2, [sp, #0x60]
0207c95c: str      x9, [sp, #0x70]
0207c960: bl       #0x27fbfd4 ; System.Collections.Generic.List<FishData>$$set_Item
0207c964: ldp      x20, x19, [sp, #0xa0]
0207c968: ldp      x22, x21, [sp, #0x90]
0207c96c: ldr      x30, [sp, #0x80]
0207c970: add      sp, sp, #0xb0
0207c974: ret
0207c978: bl       #0x18dde20

; 0x207c97c FishFlock.FishGroup$$GetFishDataIndexByTransform | int GetFishDataIndexByTransform(Transform fishTransform)
0207c97c: sub      sp, sp, #0x70
0207c980: str      x30, [sp, #0x40]
0207c984: stp      x22, x21, [sp, #0x50]
0207c988: stp      x20, x19, [sp, #0x60]
0207c98c: adrp     x21, #0x3ed5000
0207c990: ldrb     w8, [x21, #0x4e3]
0207c994: mov      x19, x1
0207c998: mov      x20, x0
0207c99c: tbnz     w8, #0, #0x207c9c0
0207c9a0: adrp     x0, #0x3c2c000
0207c9a4: ldr      x0, [x0, #0x710]
0207c9a8: bl       #0x18ddbc4
0207c9ac: adrp     x0, #0x3c2c000
0207c9b0: ldr      x0, [x0, #0x718]
0207c9b4: bl       #0x18ddbc4
0207c9b8: mov      w8, #1
0207c9bc: strb     w8, [x21, #0x4e3]
0207c9c0: ldr      x0, [x20, #0x60]
0207c9c4: cbz      x0, #0x207ca18
0207c9c8: adrp     x22, #0x3c2c000
0207c9cc: ldr      x22, [x22, #0x718]
0207c9d0: mov      w21, wzr
0207c9d4: ldr      w8, [x0, #0x18]
0207c9d8: cmp      w21, w8
0207c9dc: b.ge     #0x207ca1c
0207c9e0: ldr      x2, [x22]
0207c9e4: add      x8, sp, #8
0207c9e8: mov      w1, w21
0207c9ec: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207c9f0: ldr      x0, [sp, #0x38]
0207c9f4: cbz      x0, #0x207ca18
0207c9f8: ldr      x8, [x0]
0207c9fc: mov      x1, x19
0207ca00: ldp      x9, x2, [x8, #0x138]
0207ca04: blr      x9
0207ca08: tbnz     w0, #0, #0x207ca20
0207ca0c: ldr      x0, [x20, #0x60]
0207ca10: add      w21, w21, #1
0207ca14: cbnz     x0, #0x207c9d4
0207ca18: bl       #0x18dde20
0207ca1c: mov      w21, #-1
0207ca20: mov      w0, w21
0207ca24: ldp      x20, x19, [sp, #0x60]
0207ca28: ldp      x22, x21, [sp, #0x50]
0207ca2c: ldr      x30, [sp, #0x40]
0207ca30: add      sp, sp, #0x70
0207ca34: ret

; 0x207ca38 FishFlock.FishGroup$$.ctor | void .ctor()
0207ca38: str      x30, [sp, #-0x50]!
0207ca3c: stp      x26, x25, [sp, #0x10]
0207ca40: stp      x24, x23, [sp, #0x20]
0207ca44: stp      x22, x21, [sp, #0x30]
0207ca48: stp      x20, x19, [sp, #0x40]
0207ca4c: adrp     x26, #0x3ed5000
0207ca50: adrp     x25, #0x3c2a000
0207ca54: adrp     x20, #0x3c2c000
0207ca58: adrp     x24, #0x3bf7000
0207ca5c: adrp     x23, #0x3bf7000
0207ca60: adrp     x22, #0x3c06000
0207ca64: adrp     x21, #0x3c28000
0207ca68: ldr      x25, [x25, #0x1b8]
0207ca6c: ldrb     w8, [x26, #0x4e4]
0207ca70: ldr      x20, [x20, #0x758]
0207ca74: ldr      x24, [x24, #0xec0]
0207ca78: ldr      x23, [x23, #0xeb8]
0207ca7c: ldr      x22, [x22, #0x5b0]
0207ca80: ldr      x21, [x21, #0x28]
0207ca84: mov      x19, x0
0207ca88: tbnz     w8, #0, #0x207cadc
0207ca8c: adrp     x0, #0x3c2c000
0207ca90: ldr      x0, [x0, #0x758]
0207ca94: bl       #0x18ddbc4
0207ca98: adrp     x0, #0x3c28000
0207ca9c: ldr      x0, [x0, #0x28]
0207caa0: bl       #0x18ddbc4
0207caa4: adrp     x0, #0x3bf7000
0207caa8: ldr      x0, [x0, #0xeb8]
0207caac: bl       #0x18ddbc4
0207cab0: adrp     x0, #0x3c2a000
0207cab4: ldr      x0, [x0, #0x1b8]
0207cab8: bl       #0x18ddbc4
0207cabc: adrp     x0, #0x3c06000
0207cac0: ldr      x0, [x0, #0x5b0]
0207cac4: bl       #0x18ddbc4
0207cac8: adrp     x0, #0x3bf7000
0207cacc: ldr      x0, [x0, #0xec0]
0207cad0: bl       #0x18ddbc4
0207cad4: mov      w8, #1
0207cad8: strb     w8, [x26, #0x4e4]
0207cadc: adrp     x9, #0x981000
0207cae0: adrp     x10, #0x97f000
0207cae4: ldr      q0, [x9, #0xa80]
0207cae8: ldr      d1, [x10, #0x580]
0207caec: mov      w8, #0x101
0207caf0: mov      w26, #1
0207caf4: mov      w11, #0x40800000
0207caf8: mov      w12, #0x41200000
0207cafc: strh     w8, [x19, #0x24]
0207cb00: strb     w26, [x19, #0x26]
0207cb04: str      w11, [x19, #0x44]
0207cb08: stur     q0, [x19, #0x28]
0207cb0c: stur     d1, [x19, #0x3c]
0207cb10: str      w12, [x19, #0x50]
0207cb14: ldr      x0, [x25]
0207cb18: bl       #0x18dde10
0207cb1c: ldr      x1, [x20]
0207cb20: mov      x20, x0
0207cb24: bl       #0x27fba00 ; System.Collections.Generic.List<FishData>$$.ctor
0207cb28: mov      x0, x19
0207cb2c: str      x20, [x0, #0x60]!
0207cb30: mov      x1, x20
0207cb34: bl       #0x18ddb68
0207cb38: mov      w8, #0xcccd
0207cb3c: movk     w8, #0x3f4c, lsl #16
0207cb40: strb     w26, [x19, #0x68]
0207cb44: str      w8, [x19, #0x6c]
0207cb48: ldr      x0, [x24]
0207cb4c: bl       #0x18dde10
0207cb50: ldr      x1, [x23]
0207cb54: mov      x20, x0
0207cb58: bl       #0x281f960 ; System.Collections.Generic.List<object>$$.ctor
0207cb5c: mov      x0, x19
0207cb60: str      x20, [x0, #0x70]!
0207cb64: mov      x1, x20
0207cb68: bl       #0x18ddb68
0207cb6c: strb     w26, [x19, #0x80]
0207cb70: ldr      x0, [x22]
0207cb74: bl       #0x18dde10
0207cb78: ldr      x1, [x21]
0207cb7c: mov      x20, x0
0207cb80: bl       #0x28715d4 ; System.Collections.Generic.List<Vector3>$$.ctor
0207cb84: mov      x0, x19
0207cb88: str      x20, [x0, #0x88]!
0207cb8c: mov      x1, x20
0207cb90: bl       #0x18ddb68
0207cb94: mov      x8, #2
0207cb98: movk     x8, #5, lsl #32
0207cb9c: str      x8, [x19, #0xa0]
0207cba0: mov      x0, x19
0207cba4: ldp      x20, x19, [sp, #0x40]
0207cba8: ldp      x22, x21, [sp, #0x30]
0207cbac: ldp      x24, x23, [sp, #0x20]
0207cbb0: ldp      x26, x25, [sp, #0x10]
0207cbb4: mov      x1, xzr
0207cbb8: ldr      x30, [sp], #0x50
0207cbbc: b        #0x39112c0 ; UnityEngine.MonoBehaviour$$.ctor

; 0x207cbc0 FishFlock.FishGroupController$$Start | void Start()
0207cbc0: str      x30, [sp, #-0x30]!
0207cbc4: stp      x22, x21, [sp, #0x10]
0207cbc8: stp      x20, x19, [sp, #0x20]
0207cbcc: adrp     x20, #0x3ed5000
0207cbd0: adrp     x22, #0x3c2c000
0207cbd4: adrp     x21, #0x3bf7000
0207cbd8: ldrb     w8, [x20, #0x4e5]
0207cbdc: ldr      x22, [x22, #0x760]
0207cbe0: ldr      x21, [x21, #0x468]
0207cbe4: mov      x19, x0
0207cbe8: tbnz     w8, #0, #0x207cc18
0207cbec: adrp     x0, #0x3c2c000
0207cbf0: ldr      x0, [x0, #0x760]
0207cbf4: bl       #0x18ddbc4
0207cbf8: adrp     x0, #0x3c2c000
0207cbfc: ldr      x0, [x0, #0x768]
0207cc00: bl       #0x18ddbc4
0207cc04: adrp     x0, #0x3bf7000
0207cc08: ldr      x0, [x0, #0x468]
0207cc0c: bl       #0x18ddbc4
0207cc10: mov      w8, #1
0207cc14: strb     w8, [x20, #0x4e5]
0207cc18: ldr      x1, [x22]
0207cc1c: mov      x0, x19
0207cc20: bl       #0x228e4cc ; UnityEngine.Component$$GetComponentInParent<object>
0207cc24: mov      x20, x19
0207cc28: str      x0, [x20, #0x48]!
0207cc2c: mov      x1, x0
0207cc30: mov      x0, x20
0207cc34: bl       #0x18ddb68
0207cc38: ldr      x0, [x21]
0207cc3c: ldr      x20, [x20]
0207cc40: ldr      w8, [x0, #0xe0]
0207cc44: cbnz     w8, #0x207cc4c
0207cc48: bl       #0x18ddcfc
0207cc4c: mov      x0, x20
0207cc50: mov      x1, xzr
0207cc54: mov      x2, xzr
0207cc58: bl       #0x39106d8 ; UnityEngine.Object$$op_Equality
0207cc5c: tbz      w0, #0, #0x207cc70
0207cc60: ldp      x20, x19, [sp, #0x20]
0207cc64: ldp      x22, x21, [sp, #0x10]
0207cc68: ldr      x30, [sp], #0x30
0207cc6c: ret
0207cc70: adrp     x8, #0x3c2c000
0207cc74: ldr      x8, [x8, #0x768]
0207cc78: mov      x0, x19
0207cc7c: ldr      x1, [x8]
0207cc80: bl       #0x228de10 ; UnityEngine.Component$$GetComponent<object>
0207cc84: mov      x20, x19
0207cc88: str      x0, [x20, #0x40]!
0207cc8c: mov      x1, x0
0207cc90: mov      x0, x20
0207cc94: bl       #0x18ddb68
0207cc98: ldr      x0, [x20, #8]
0207cc9c: cbz      x0, #0x207ccbc
0207cca0: ldr      x1, [x19, #0x40]
0207cca4: bl       #0x207ccc0 ; FishFlock.FishFlockController$$AddFishGroup
0207cca8: mov      x0, x19
0207ccac: ldp      x20, x19, [sp, #0x20]
0207ccb0: ldp      x22, x21, [sp, #0x10]
0207ccb4: ldr      x30, [sp], #0x30
0207ccb8: b        #0x207cdb0 ; FishFlock.FishGroupController$$ResetFish
0207ccbc: bl       #0x18dde20

; 0x207cdb0 FishFlock.FishGroupController$$ResetFish | void ResetFish()
0207cdb0: sub      sp, sp, #0x80
0207cdb4: stp      x30, x25, [sp, #0x40]
0207cdb8: stp      x24, x23, [sp, #0x50]
0207cdbc: stp      x22, x21, [sp, #0x60]
0207cdc0: stp      x20, x19, [sp, #0x70]
0207cdc4: adrp     x20, #0x3ed5000
0207cdc8: adrp     x23, #0x3bf7000
0207cdcc: ldrb     w8, [x20, #0x4e6]
0207cdd0: ldr      x23, [x23, #0x468]
0207cdd4: mov      x19, x0
0207cdd8: tbnz     w8, #0, #0x207ce08
0207cddc: adrp     x0, #0x3c23000
0207cde0: ldr      x0, [x0, #0xb90]
0207cde4: bl       #0x18ddbc4
0207cde8: adrp     x0, #0x3c2c000
0207cdec: ldr      x0, [x0, #0x718]
0207cdf0: bl       #0x18ddbc4
0207cdf4: adrp     x0, #0x3bf7000
0207cdf8: ldr      x0, [x0, #0x468]
0207cdfc: bl       #0x18ddbc4
0207ce00: mov      w8, #1
0207ce04: strb     w8, [x20, #0x4e6]
0207ce08: ldr      x0, [x23]
0207ce0c: ldr      x20, [x19, #0x20]
0207ce10: ldr      w8, [x0, #0xe0]
0207ce14: cbnz     w8, #0x207ce1c
0207ce18: bl       #0x18ddcfc
0207ce1c: mov      x0, x20
0207ce20: mov      x1, xzr
0207ce24: mov      x2, xzr
0207ce28: bl       #0x390f060 ; UnityEngine.Object$$op_Inequality
0207ce2c: tbz      w0, #0, #0x207d078
0207ce30: ldr      x0, [x23]
0207ce34: ldr      x20, [x19, #0x40]
0207ce38: ldr      w8, [x0, #0xe0]
0207ce3c: cbnz     w8, #0x207ce44
0207ce40: bl       #0x18ddcfc
0207ce44: mov      x0, x20
0207ce48: mov      x1, xzr
0207ce4c: mov      x2, xzr
0207ce50: bl       #0x390f060 ; UnityEngine.Object$$op_Inequality
0207ce54: tbz      w0, #0, #0x207d078
0207ce58: ldr      x0, [x19, #0x40]
0207ce5c: cbz      x0, #0x207d090
0207ce60: bl       #0x207c74c ; FishFlock.FishGroup$$GetFishCount
0207ce64: ldr      w8, [x19, #0x28]
0207ce68: subs     w20, w0, w8
0207ce6c: b.le     #0x207ce88
0207ce70: ldr      x0, [x19, #0x40]
0207ce74: cbz      x0, #0x207d090
0207ce78: mov      w1, wzr
0207ce7c: bl       #0x207c630 ; FishFlock.FishGroup$$RemoveFish
0207ce80: subs     w20, w20, #1
0207ce84: b.ne     #0x207ce70
0207ce88: ldr      x0, [x19, #0x40]
0207ce8c: cbz      x0, #0x207d090
0207ce90: bl       #0x207c74c ; FishFlock.FishGroup$$GetFishCount
0207ce94: mov      w20, w0
0207ce98: cmp      w0, #1
0207ce9c: b.lt     #0x207cf90
0207cea0: adrp     x24, #0x3c2c000
0207cea4: adrp     x25, #0x3c23000
0207cea8: ldr      x24, [x24, #0x718]
0207ceac: ldr      x25, [x25, #0xb90]
0207ceb0: mov      w21, wzr
0207ceb4: ldp      s0, s1, [x19, #0x38]
0207ceb8: ldr      x22, [x19, #0x40]
0207cebc: mov      x0, xzr
0207cec0: bl       #0x390b098 ; UnityEngine.Random$$Range
0207cec4: cbz      x22, #0x207d090
0207cec8: mov      x0, x22
0207cecc: mov      w1, w21
0207ced0: bl       #0x207c548 ; FishFlock.FishGroup$$SetScale
0207ced4: ldr      x0, [x19, #0x30]
0207ced8: mov      x1, xzr
0207cedc: bl       #0x2e79b7c ; System.String$$IsNullOrEmpty
0207cee0: tbnz     w0, #0, #0x207cf84
0207cee4: ldr      x8, [x19, #0x40]
0207cee8: cbz      x8, #0x207d090
0207ceec: ldr      x0, [x8, #0x60]
0207cef0: cbz      x0, #0x207d090
0207cef4: ldr      x2, [x24]
0207cef8: add      x8, sp, #8
0207cefc: mov      w1, w21
0207cf00: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207cf04: ldr      x0, [sp, #0x38]
0207cf08: cbz      x0, #0x207d090
0207cf0c: ldr      x1, [x25]
0207cf10: bl       #0x228de10 ; UnityEngine.Component$$GetComponent<object>
0207cf14: ldr      x8, [x23]
0207cf18: mov      x22, x0
0207cf1c: ldr      w9, [x8, #0xe0]
0207cf20: cbnz     w9, #0x207cf2c
0207cf24: mov      x0, x8
0207cf28: bl       #0x18ddcfc
0207cf2c: mov      x0, x22
0207cf30: mov      x1, xzr
0207cf34: mov      x2, xzr
0207cf38: bl       #0x390f060 ; UnityEngine.Object$$op_Inequality
0207cf3c: tbz      w0, #0, #0x207cf84
0207cf40: ldr      x0, [x19, #0x30]
0207cf44: mov      x1, xzr
0207cf48: bl       #0x389bd40 ; UnityEngine.Animator$$StringToHash
0207cf4c: cbz      x22, #0x207d090
0207cf50: mov      w2, w0
0207cf54: mov      x0, x22
0207cf58: mov      w1, wzr
0207cf5c: mov      x3, xzr
0207cf60: bl       #0x38a0a9c ; UnityEngine.Animator$$HasState
0207cf64: tbz      w0, #0, #0x207cf84
0207cf68: ldr      x0, [x19, #0x30]
0207cf6c: mov      x1, xzr
0207cf70: bl       #0x389bd40 ; UnityEngine.Animator$$StringToHash
0207cf74: mov      w1, w0
0207cf78: mov      x0, x22
0207cf7c: mov      x2, xzr
0207cf80: bl       #0x38a0050 ; UnityEngine.Animator$$Play
0207cf84: add      w21, w21, #1
0207cf88: cmp      w20, w21
0207cf8c: b.ne     #0x207ceb4
0207cf90: ldr      w8, [x19, #0x28]
0207cf94: cmp      w20, w8
0207cf98: b.ge     #0x207d070
0207cf9c: adrp     x24, #0x3c23000
0207cfa0: ldr      x24, [x24, #0xb90]
0207cfa4: ldp      s0, s1, [x19, #0x38]
0207cfa8: ldr      x21, [x19, #0x40]
0207cfac: ldr      x22, [x19, #0x20]
0207cfb0: mov      x0, xzr
0207cfb4: bl       #0x390b098 ; UnityEngine.Random$$Range
0207cfb8: cbz      x21, #0x207d090
0207cfbc: add      x8, sp, #8
0207cfc0: mov      x0, x21
0207cfc4: mov      x1, x22
0207cfc8: bl       #0x207be38 ; FishFlock.FishGroup$$AddFish
0207cfcc: ldr      x0, [x19, #0x30]
0207cfd0: ldr      x21, [sp, #0x38]
0207cfd4: mov      x1, xzr
0207cfd8: bl       #0x2e79b7c ; System.String$$IsNullOrEmpty
0207cfdc: tbnz     w0, #0, #0x207d060
0207cfe0: cbz      x21, #0x207d090
0207cfe4: ldr      x1, [x24]
0207cfe8: mov      x0, x21
0207cfec: bl       #0x228de10 ; UnityEngine.Component$$GetComponent<object>
0207cff0: ldr      x8, [x23]
0207cff4: mov      x21, x0
0207cff8: ldr      w9, [x8, #0xe0]
0207cffc: cbnz     w9, #0x207d008
0207d000: mov      x0, x8
0207d004: bl       #0x18ddcfc
0207d008: mov      x0, x21
0207d00c: mov      x1, xzr
0207d010: mov      x2, xzr
0207d014: bl       #0x390f060 ; UnityEngine.Object$$op_Inequality
0207d018: tbz      w0, #0, #0x207d060
0207d01c: ldr      x0, [x19, #0x30]
0207d020: mov      x1, xzr
0207d024: bl       #0x389bd40 ; UnityEngine.Animator$$StringToHash
0207d028: cbz      x21, #0x207d090
0207d02c: mov      w2, w0
0207d030: mov      x0, x21
0207d034: mov      w1, wzr
0207d038: mov      x3, xzr
0207d03c: bl       #0x38a0a9c ; UnityEngine.Animator$$HasState
0207d040: tbz      w0, #0, #0x207d060
0207d044: ldr      x0, [x19, #0x30]
0207d048: mov      x1, xzr
0207d04c: bl       #0x389bd40 ; UnityEngine.Animator$$StringToHash
0207d050: mov      w1, w0
0207d054: mov      x0, x21
0207d058: mov      x2, xzr
0207d05c: bl       #0x38a0050 ; UnityEngine.Animator$$Play
0207d060: ldr      w8, [x19, #0x28]
0207d064: add      w20, w20, #1
0207d068: cmp      w20, w8
0207d06c: b.lt     #0x207cfa4
0207d070: ldr      x8, [x19, #0x38]
0207d074: str      x8, [x19, #0x50]
0207d078: ldp      x20, x19, [sp, #0x70]
0207d07c: ldp      x22, x21, [sp, #0x60]
0207d080: ldp      x24, x23, [sp, #0x50]
0207d084: ldp      x30, x25, [sp, #0x40]
0207d088: add      sp, sp, #0x80
0207d08c: ret
0207d090: bl       #0x18dde20

; 0x207d094 FishFlock.FishGroupController$$OnValidate | void OnValidate()
0207d094: b        #0x207cdb0 ; FishFlock.FishGroupController$$ResetFish

; 0x207d098 FishFlock.FishGroupController$$.ctor | void .ctor()
0207d098: stp      x30, x21, [sp, #-0x20]!
0207d09c: stp      x20, x19, [sp, #0x10]
0207d0a0: adrp     x20, #0x3ed5000
0207d0a4: adrp     x21, #0x3c2c000
0207d0a8: ldrb     w8, [x20, #0x4e7]
0207d0ac: ldr      x21, [x21, #0x780]
0207d0b0: mov      x19, x0
0207d0b4: tbnz     w8, #0, #0x207d0cc
0207d0b8: adrp     x0, #0x3c2c000
0207d0bc: ldr      x0, [x0, #0x780]
0207d0c0: bl       #0x18ddbc4
0207d0c4: mov      w8, #1
0207d0c8: strb     w8, [x20, #0x4e7]
0207d0cc: ldr      x1, [x21]
0207d0d0: mov      x20, x19
0207d0d4: str      x1, [x20, #0x30]!
0207d0d8: mov      x0, x20
0207d0dc: bl       #0x18ddb68
0207d0e0: adrp     x8, #0x97f000
0207d0e4: ldr      d0, [x8, #0x370]
0207d0e8: str      d0, [x20, #8]
0207d0ec: adrp     x20, #0x3ed1000
0207d0f0: ldrb     w8, [x20, #0x992]
0207d0f4: cbnz     w8, #0x207d10c
0207d0f8: adrp     x0, #0x3bf8000
0207d0fc: ldr      x0, [x0, #0x730]
0207d100: bl       #0x18ddbc4
0207d104: mov      w8, #1
0207d108: strb     w8, [x20, #0x992]
0207d10c: adrp     x8, #0x3bf8000
0207d110: ldr      x8, [x8, #0x730]
0207d114: mov      x0, x19
0207d118: mov      x1, xzr
0207d11c: ldr      x8, [x8]
0207d120: ldr      x8, [x8, #0xb8]
0207d124: ldr      d0, [x8]
0207d128: str      d0, [x19, #0x50]
0207d12c: ldp      x20, x19, [sp, #0x10]
0207d130: ldp      x30, x21, [sp], #0x20
0207d134: b        #0x39112c0 ; UnityEngine.MonoBehaviour$$.ctor

; 0x207d138 FishFlock.FlockGfxProfile$$.ctor | void .ctor()
0207d138: mov      w8, #1
0207d13c: mov      x1, xzr
0207d140: str      w8, [x0, #0x30]
0207d144: strb     w8, [x0, #0x34]
0207d148: b        #0x39113b4 ; UnityEngine.ScriptableObject$$.ctor

; 0x207d14c FishFlock.FishFlockController$$Awake | void Awake()
0207d14c: stp      x30, x21, [sp, #-0x20]!
0207d150: stp      x20, x19, [sp, #0x10]
0207d154: adrp     x20, #0x3ed5000
0207d158: ldrb     w8, [x20, #0x4e8]
0207d15c: mov      x19, x0
0207d160: tbnz     w8, #0, #0x207d1a8
0207d164: adrp     x0, #0x3c2c000
0207d168: ldr      x0, [x0, #0x788]
0207d16c: bl       #0x18ddbc4
0207d170: adrp     x0, #0x3bfe000
0207d174: ldr      x0, [x0, #0xdb0]
0207d178: bl       #0x18ddbc4
0207d17c: adrp     x0, #0x3c2c000
0207d180: ldr      x0, [x0, #0x790]
0207d184: bl       #0x18ddbc4
0207d188: adrp     x0, #0x3c2c000
0207d18c: ldr      x0, [x0, #0x798]
0207d190: bl       #0x18ddbc4
0207d194: adrp     x0, #0x3bf8000
0207d198: ldr      x0, [x0, #0x248]
0207d19c: bl       #0x18ddbc4
0207d1a0: mov      w8, #1
0207d1a4: strb     w8, [x20, #0x4e8]
0207d1a8: ldr      x0, [x19, #0x70]
0207d1ac: cbz      x0, #0x207d27c
0207d1b0: adrp     x8, #0x980000
0207d1b4: ldr      s0, [x8, #0x96c]
0207d1b8: mov      x1, xzr
0207d1bc: bl       #0x19a22b0 ; SimpleCounter$$Start
0207d1c0: mov      x20, x19
0207d1c4: ldr      x8, [x20, #0x50]!
0207d1c8: cbnz     x8, #0x207d1f0
0207d1cc: adrp     x8, #0x3c2c000
0207d1d0: ldr      x8, [x8, #0x788]
0207d1d4: mov      w1, wzr
0207d1d8: ldr      x0, [x8]
0207d1dc: bl       #0x18ddc6c
0207d1e0: mov      x1, x0
0207d1e4: str      x0, [x20]
0207d1e8: mov      x0, x20
0207d1ec: bl       #0x18ddb68
0207d1f0: ldr      x8, [x19, #0x88]
0207d1f4: cbz      x8, #0x207d27c
0207d1f8: adrp     x9, #0x3bf8000
0207d1fc: ldr      x9, [x9, #0x248]
0207d200: adrp     x21, #0x3bfe000
0207d204: ldr      w20, [x8, #0x18]
0207d208: ldr      x0, [x9]
0207d20c: ldr      x21, [x21, #0xdb0]
0207d210: bl       #0x18dde10
0207d214: ldr      x2, [x21]
0207d218: mov      w1, w20
0207d21c: mov      x21, x0
0207d220: bl       #0x2807c40 ; System.Collections.Generic.List<int>$$.ctor
0207d224: mov      x20, x19
0207d228: str      x21, [x20, #0x90]!
0207d22c: mov      x0, x20
0207d230: mov      x1, x21
0207d234: bl       #0x18ddb68
0207d238: ldur     x0, [x20, #-8]
0207d23c: cbz      x0, #0x207d27c
0207d240: adrp     x21, #0x3c2c000
0207d244: ldr      x21, [x21, #0x798]
0207d248: mov      w20, wzr
0207d24c: ldr      w8, [x0, #0x18]
0207d250: cmp      w20, w8
0207d254: b.ge     #0x207d280
0207d258: ldr      x2, [x21]
0207d25c: mov      w1, w20
0207d260: bl       #0x281fec4 ; System.Collections.Generic.List<object>$$get_Item
0207d264: cbz      x0, #0x207d27c
0207d268: mov      x1, x19
0207d26c: bl       #0x207ab94 ; FishFlock.FishGroup$$Init
0207d270: ldr      x0, [x19, #0x88]
0207d274: add      w20, w20, #1
0207d278: cbnz     x0, #0x207d24c
0207d27c: bl       #0x18dde20
0207d280: mov      x0, x19
0207d284: bl       #0x207d2a0 ; FishFlock.FishFlockController$$InitializeFishes
0207d288: mov      x0, x19
0207d28c: bl       #0x207d33c ; FishFlock.FishFlockController$$UpdateCollisionData
0207d290: mov      x0, x19
0207d294: ldp      x20, x19, [sp, #0x10]
0207d298: ldp      x30, x21, [sp], #0x20
0207d29c: b        #0x207d7b8 ; FishFlock.FishFlockController$$CreateCollisionData

; 0x207ccc0 FishFlock.FishFlockController$$AddFishGroup | void AddFishGroup(FishGroup fishGroup)
0207ccc0: stp      x30, x21, [sp, #-0x20]!
0207ccc4: stp      x20, x19, [sp, #0x10]
0207ccc8: adrp     x21, #0x3ed5000
0207cccc: ldrb     w8, [x21, #0x4e9]
0207ccd0: mov      x19, x1
0207ccd4: mov      x20, x0
0207ccd8: tbnz     w8, #0, #0x207ccfc
0207ccdc: adrp     x0, #0x3c2c000
0207cce0: ldr      x0, [x0, #0x770]
0207cce4: bl       #0x18ddbc4
0207cce8: adrp     x0, #0x3c2c000
0207ccec: ldr      x0, [x0, #0x778]
0207ccf0: bl       #0x18ddbc4
0207ccf4: mov      w8, #1
0207ccf8: strb     w8, [x21, #0x4e9]
0207ccfc: ldr      x0, [x20, #0x88]
0207cd00: cbz      x0, #0x207cdac
0207cd04: adrp     x8, #0x3c2c000
0207cd08: ldr      x8, [x8, #0x778]
0207cd0c: mov      x1, x19
0207cd10: ldr      x2, [x8]
0207cd14: bl       #0x2820524 ; System.Collections.Generic.List<object>$$Contains
0207cd18: tbz      w0, #0, #0x207cd28
0207cd1c: ldp      x20, x19, [sp, #0x10]
0207cd20: ldp      x30, x21, [sp], #0x20
0207cd24: ret
0207cd28: ldr      x0, [x20, #0x88]
0207cd2c: cbz      x0, #0x207cdac
0207cd30: adrp     x9, #0x3c2c000
0207cd34: ldr      x9, [x9, #0x770]
0207cd38: ldr      w10, [x0, #0x1c]
0207cd3c: ldr      x8, [x0, #0x10]
0207cd40: ldr      x9, [x9]
0207cd44: add      w10, w10, #1
0207cd48: str      w10, [x0, #0x1c]
0207cd4c: cbz      x8, #0x207cdac
0207cd50: ldrsw    x10, [x0, #0x18]
0207cd54: ldr      w11, [x8, #0x18]
0207cd58: cmp      w10, w11
0207cd5c: b.hs     #0x207cd80
0207cd60: add      w9, w10, #1
0207cd64: add      x8, x8, x10, lsl #3
0207cd68: str      w9, [x0, #0x18]
0207cd6c: str      x19, [x8, #0x20]!
0207cd70: mov      x0, x8
0207cd74: mov      x1, x19
0207cd78: bl       #0x18ddb68
0207cd7c: b        #0x207cd94
0207cd80: ldr      x8, [x9, #0x20]
0207cd84: mov      x1, x19
0207cd88: ldr      x8, [x8, #0xc0]
0207cd8c: ldr      x2, [x8, #0x70]
0207cd90: bl       #0x2820194 ; System.Collections.Generic.List<object>$$AddWithResize
0207cd94: cbz      x19, #0x207cdac
0207cd98: mov      x0, x19
0207cd9c: mov      x1, x20
0207cda0: ldp      x20, x19, [sp, #0x10]
0207cda4: ldp      x30, x21, [sp], #0x20
0207cda8: b        #0x207ab94 ; FishFlock.FishGroup$$Init
0207cdac: bl       #0x18dde20

; 0x207d84c FishFlock.FishFlockController$$RemoveFishGroup | void RemoveFishGroup(FishGroup fishGroup)
0207d84c: stp      x30, x21, [sp, #-0x20]!
0207d850: stp      x20, x19, [sp, #0x10]
0207d854: adrp     x21, #0x3ed5000
0207d858: ldrb     w8, [x21, #0x4ea]
0207d85c: mov      x19, x1
0207d860: mov      x20, x0
0207d864: tbnz     w8, #0, #0x207d87c
0207d868: adrp     x0, #0x3c2c000
0207d86c: ldr      x0, [x0, #0x7c0]
0207d870: bl       #0x18ddbc4
0207d874: mov      w8, #1
0207d878: strb     w8, [x21, #0x4ea]
0207d87c: ldr      x0, [x20, #0x88]
0207d880: cbz      x0, #0x207d8a0
0207d884: adrp     x8, #0x3c2c000
0207d888: ldr      x8, [x8, #0x7c0]
0207d88c: mov      x1, x19
0207d890: ldp      x20, x19, [sp, #0x10]
0207d894: ldr      x2, [x8]
0207d898: ldp      x30, x21, [sp], #0x20
0207d89c: b        #0x2821a24 ; System.Collections.Generic.List<object>$$Remove
0207d8a0: bl       #0x18dde20

; 0x207d8a4 FishFlock.FishFlockController$$AddCollider | void AddCollider(Collider collider)
0207d8a4: str      x30, [sp, #-0x50]!
0207d8a8: stp      x26, x25, [sp, #0x10]
0207d8ac: stp      x24, x23, [sp, #0x20]
0207d8b0: stp      x22, x21, [sp, #0x30]
0207d8b4: stp      x20, x19, [sp, #0x40]
0207d8b8: adrp     x21, #0x3ed5000
0207d8bc: ldrb     w8, [x21, #0x4eb]
0207d8c0: mov      x20, x1
0207d8c4: mov      x19, x0
0207d8c8: tbnz     w8, #0, #0x207d8ec
0207d8cc: adrp     x0, #0x3c2c000
0207d8d0: ldr      x0, [x0, #0x788]
0207d8d4: bl       #0x18ddbc4
0207d8d8: adrp     x0, #0x3bf7000
0207d8dc: ldr      x0, [x0, #0x468]
0207d8e0: bl       #0x18ddbc4
0207d8e4: mov      w8, #1
0207d8e8: strb     w8, [x21, #0x4eb]
0207d8ec: mov      x21, x19
0207d8f0: ldr      x23, [x21, #0x50]!
0207d8f4: cbz      x23, #0x207d954
0207d8f8: adrp     x25, #0x3bf7000
0207d8fc: ldr      x25, [x25, #0x468]
0207d900: mov      x24, xzr
0207d904: ldr      w8, [x23, #0x18]
0207d908: cmp      x24, w8, sxtw
0207d90c: b.ge     #0x207d9b0
0207d910: cmp      x24, x8
0207d914: b.hs     #0x207dac8
0207d918: ldr      x0, [x25]
0207d91c: add      x8, x23, x24, lsl #3
0207d920: ldr      x22, [x8, #0x20]
0207d924: ldr      w9, [x0, #0xe0]
0207d928: cbnz     w9, #0x207d930
0207d92c: bl       #0x18ddcfc
0207d930: mov      x0, x20
0207d934: mov      x1, x22
0207d938: mov      x2, xzr
0207d93c: bl       #0x39106d8 ; UnityEngine.Object$$op_Equality
0207d940: tbnz     w0, #0, #0x207dab0
0207d944: ldr      x23, [x21]
0207d948: add      x24, x24, #1
0207d94c: cbnz     x23, #0x207d904
0207d950: bl       #0x18dde20
0207d954: adrp     x8, #0x3c2c000
0207d958: ldr      x8, [x8, #0x788]
0207d95c: mov      w1, #1
0207d960: ldr      x0, [x8]
0207d964: bl       #0x18ddc6c
0207d968: cbz      x0, #0x207d950
0207d96c: mov      x22, x0
0207d970: cbz      x20, #0x207d988
0207d974: ldr      x8, [x22]
0207d978: mov      x0, x20
0207d97c: ldr      x1, [x8, #0x40]
0207d980: bl       #0x18ddd00
0207d984: cbz      x0, #0x207dacc
0207d988: ldr      w8, [x22, #0x18]
0207d98c: cbz      w8, #0x207dac8
0207d990: mov      x0, x22
0207d994: str      x20, [x0, #0x20]!
0207d998: mov      x1, x20
0207d99c: bl       #0x18ddb68
0207d9a0: str      x22, [x21]
0207d9a4: mov      x0, x21
0207d9a8: mov      x1, x22
0207d9ac: b        #0x207da88
0207d9b0: adrp     x9, #0x3c2c000
0207d9b4: ldr      x9, [x9, #0x788]
0207d9b8: add      w1, w8, #1
0207d9bc: ldr      x0, [x9]
0207d9c0: bl       #0x18ddc6c
0207d9c4: mov      x1, x0
0207d9c8: str      x0, [x21]
0207d9cc: mov      x0, x21
0207d9d0: bl       #0x18ddb68
0207d9d4: ldr      x8, [x23, #0x18]
0207d9d8: ldr      x24, [x21]
0207d9dc: cmp      w8, #1
0207d9e0: and      x8, x8, #0xffffffff
0207d9e4: b.lt     #0x207da4c
0207d9e8: mov      x25, xzr
0207d9ec: mov      w26, #0x20
0207d9f0: cmp      x25, w8, uxtw
0207d9f4: b.hs     #0x207dac8
0207d9f8: cbz      x24, #0x207d950
0207d9fc: ldr      x22, [x23, x26]
0207da00: cbz      x22, #0x207da18
0207da04: ldr      x8, [x24]
0207da08: mov      x0, x22
0207da0c: ldr      x1, [x8, #0x40]
0207da10: bl       #0x18ddd00
0207da14: cbz      x0, #0x207dacc
0207da18: ldr      w8, [x24, #0x18]
0207da1c: cmp      x25, x8
0207da20: b.hs     #0x207dac8
0207da24: add      x0, x24, x26
0207da28: mov      x1, x22
0207da2c: str      x22, [x0]
0207da30: bl       #0x18ddb68
0207da34: ldr      w8, [x23, #0x18]
0207da38: ldr      x24, [x21]
0207da3c: add      x25, x25, #1
0207da40: add      x26, x26, #8
0207da44: cmp      x25, w8, sxtw
0207da48: b.lt     #0x207d9f0
0207da4c: cbz      x24, #0x207d950
0207da50: cbz      x20, #0x207da6c
0207da54: ldr      x8, [x24]
0207da58: mov      x0, x20
0207da5c: ldr      x1, [x8, #0x40]
0207da60: bl       #0x18ddd00
0207da64: cbz      x0, #0x207dacc
0207da68: ldr      x8, [x23, #0x18]
0207da6c: ldr      w9, [x24, #0x18]
0207da70: cmp      w8, w9
0207da74: b.hs     #0x207dac8
0207da78: lsl      x8, x8, #0x20
0207da7c: add      x0, x24, x8, asr #29
0207da80: str      x20, [x0, #0x20]!
0207da84: mov      x1, x20
0207da88: bl       #0x18ddb68
0207da8c: mov      x0, x19
0207da90: bl       #0x207d33c ; FishFlock.FishFlockController$$UpdateCollisionData
0207da94: mov      x0, x19
0207da98: ldp      x20, x19, [sp, #0x40]
0207da9c: ldp      x22, x21, [sp, #0x30]
0207daa0: ldp      x24, x23, [sp, #0x20]
0207daa4: ldp      x26, x25, [sp, #0x10]
0207daa8: ldr      x30, [sp], #0x50
0207daac: b        #0x207d7b8 ; FishFlock.FishFlockController$$CreateCollisionData
0207dab0: ldp      x20, x19, [sp, #0x40]
0207dab4: ldp      x22, x21, [sp, #0x30]
0207dab8: ldp      x24, x23, [sp, #0x20]
0207dabc: ldp      x26, x25, [sp, #0x10]
0207dac0: ldr      x30, [sp], #0x50
0207dac4: ret
0207dac8: bl       #0x18dde28
0207dacc: bl       #0x18dde44
0207dad0: mov      x1, xzr
0207dad4: bl       #0x18ddcec

; 0x207dad8 FishFlock.FishFlockController$$RemoveCollider | void RemoveCollider(Collider collider)
0207dad8: str      x30, [sp, #-0x50]!
0207dadc: stp      x26, x25, [sp, #0x10]
0207dae0: stp      x24, x23, [sp, #0x20]
0207dae4: stp      x22, x21, [sp, #0x30]
0207dae8: stp      x20, x19, [sp, #0x40]
0207daec: adrp     x20, #0x3ed5000
0207daf0: ldrb     w8, [x20, #0x4ec]
0207daf4: mov      x21, x1
0207daf8: mov      x19, x0
0207dafc: tbnz     w8, #0, #0x207db20
0207db00: adrp     x0, #0x3c2c000
0207db04: ldr      x0, [x0, #0x788]
0207db08: bl       #0x18ddbc4
0207db0c: adrp     x0, #0x3bf7000
0207db10: ldr      x0, [x0, #0x468]
0207db14: bl       #0x18ddbc4
0207db18: mov      w8, #1
0207db1c: strb     w8, [x20, #0x4ec]
0207db20: mov      x20, x19
0207db24: ldr      x8, [x20, #0x50]!
0207db28: cbz      x8, #0x207dc88
0207db2c: adrp     x24, #0x3bf7000
0207db30: ldr      x24, [x24, #0x468]
0207db34: mov      x23, xzr
0207db38: ldr      w9, [x8, #0x18]
0207db3c: cmp      x23, w9, sxtw
0207db40: b.ge     #0x207dc88
0207db44: cmp      x23, x9
0207db48: b.hs     #0x207dcc4
0207db4c: ldr      x0, [x24]
0207db50: add      x8, x8, x23, lsl #3
0207db54: ldr      x22, [x8, #0x20]
0207db58: ldr      w9, [x0, #0xe0]
0207db5c: cbnz     w9, #0x207db64
0207db60: bl       #0x18ddcfc
0207db64: mov      x0, x21
0207db68: mov      x1, x22
0207db6c: mov      x2, xzr
0207db70: bl       #0x39106d8 ; UnityEngine.Object$$op_Equality
0207db74: tbnz     w0, #0, #0x207db88
0207db78: ldr      x8, [x20]
0207db7c: add      x23, x23, #1
0207db80: cbnz     x8, #0x207db38
0207db84: b        #0x207dc84
0207db88: tbnz     w23, #0x1f, #0x207dc88
0207db8c: ldr      x22, [x20]
0207db90: cbz      x22, #0x207dc84
0207db94: adrp     x8, #0x3c2c000
0207db98: ldr      x8, [x8, #0x788]
0207db9c: ldr      w9, [x22, #0x18]
0207dba0: ldr      x0, [x8]
0207dba4: sub      w1, w9, #1
0207dba8: bl       #0x18ddc6c
0207dbac: mov      x1, x0
0207dbb0: str      x0, [x20]
0207dbb4: mov      x0, x20
0207dbb8: bl       #0x18ddb68
0207dbbc: ldr      x25, [x20]
0207dbc0: cbz      x25, #0x207dc84
0207dbc4: mov      x24, xzr
0207dbc8: ldr      w8, [x25, #0x18]
0207dbcc: cmp      x24, w8, sxtw
0207dbd0: b.ge     #0x207dca0
0207dbd4: cmp      x24, x23
0207dbd8: b.hs     #0x207dc2c
0207dbdc: ldr      w9, [x22, #0x18]
0207dbe0: cmp      x24, x9
0207dbe4: b.hs     #0x207dcc4
0207dbe8: add      x9, x22, x24, lsl #3
0207dbec: ldr      x21, [x9, #0x20]
0207dbf0: cbz      x21, #0x207dc0c
0207dbf4: ldr      x8, [x25]
0207dbf8: mov      x0, x21
0207dbfc: ldr      x1, [x8, #0x40]
0207dc00: bl       #0x18ddd00
0207dc04: cbz      x0, #0x207dcc8
0207dc08: ldr      w8, [x25, #0x18]
0207dc0c: cmp      x24, x8
0207dc10: b.hs     #0x207dcc4
0207dc14: add      x0, x25, x24, lsl #3
0207dc18: str      x21, [x0, #0x20]!
0207dc1c: mov      x1, x21
0207dc20: bl       #0x18ddb68
0207dc24: add      x24, x24, #1
0207dc28: b        #0x207dc7c
0207dc2c: ldr      w9, [x22, #0x18]
0207dc30: add      x26, x24, #1
0207dc34: cmp      w26, w9
0207dc38: b.hs     #0x207dcc4
0207dc3c: add      x9, x22, x26, lsl #3
0207dc40: ldr      x21, [x9, #0x20]
0207dc44: cbz      x21, #0x207dc60
0207dc48: ldr      x8, [x25]
0207dc4c: mov      x0, x21
0207dc50: ldr      x1, [x8, #0x40]
0207dc54: bl       #0x18ddd00
0207dc58: cbz      x0, #0x207dcc8
0207dc5c: ldr      w8, [x25, #0x18]
0207dc60: cmp      x24, x8
0207dc64: b.hs     #0x207dcc4
0207dc68: add      x0, x25, x24, lsl #3
0207dc6c: str      x21, [x0, #0x20]!
0207dc70: mov      x1, x21
0207dc74: bl       #0x18ddb68
0207dc78: mov      x24, x26
0207dc7c: ldr      x25, [x20]
0207dc80: cbnz     x25, #0x207dbc8
0207dc84: bl       #0x18dde20
0207dc88: ldp      x20, x19, [sp, #0x40]
0207dc8c: ldp      x22, x21, [sp, #0x30]
0207dc90: ldp      x24, x23, [sp, #0x20]
0207dc94: ldp      x26, x25, [sp, #0x10]
0207dc98: ldr      x30, [sp], #0x50
0207dc9c: ret
0207dca0: mov      x0, x19
0207dca4: bl       #0x207d33c ; FishFlock.FishFlockController$$UpdateCollisionData
0207dca8: mov      x0, x19
0207dcac: ldp      x20, x19, [sp, #0x40]
0207dcb0: ldp      x22, x21, [sp, #0x30]
0207dcb4: ldp      x24, x23, [sp, #0x20]
0207dcb8: ldp      x26, x25, [sp, #0x10]
0207dcbc: ldr      x30, [sp], #0x50
0207dcc0: b        #0x207d7b8 ; FishFlock.FishFlockController$$CreateCollisionData
0207dcc4: bl       #0x18dde28
0207dcc8: bl       #0x18dde44
0207dccc: mov      x1, xzr
0207dcd0: bl       #0x18ddcec

; 0x207d2a0 FishFlock.FishFlockController$$InitializeFishes | void InitializeFishes()
0207d2a0: str      x30, [sp, #-0x20]!
0207d2a4: stp      x20, x19, [sp, #0x10]
0207d2a8: adrp     x20, #0x3ed5000
0207d2ac: ldrb     w8, [x20, #0x4ed]
0207d2b0: mov      x19, x0
0207d2b4: tbnz     w8, #0, #0x207d2d8
0207d2b8: adrp     x0, #0x3bf8000
0207d2bc: ldr      x0, [x0, #0xaa0]
0207d2c0: bl       #0x18ddbc4
0207d2c4: adrp     x0, #0x3c2c000
0207d2c8: ldr      x0, [x0, #0x7a0]
0207d2cc: bl       #0x18ddbc4
0207d2d0: mov      w8, #1
0207d2d4: strb     w8, [x20, #0x4ed]
0207d2d8: ldr      w8, [x19, #0x34]
0207d2dc: cmp      w8, #1
0207d2e0: b.ne     #0x207d330
0207d2e4: adrp     x8, #0x3bf8000
0207d2e8: ldr      x8, [x8, #0xaa0]
0207d2ec: adrp     x20, #0x3c2c000
0207d2f0: ldr      x0, [x8]
0207d2f4: ldr      x20, [x20, #0x7a0]
0207d2f8: bl       #0x18dde10
0207d2fc: ldr      x2, [x20]
0207d300: mov      x1, x19
0207d304: mov      x3, xzr
0207d308: mov      x20, x0
0207d30c: bl       #0x2f693f4 ; System.Action$$.ctor
0207d310: mov      x0, x20
0207d314: bl       #0x207dcd4 ; FishFlock.ThreadManager$$DoTask
0207d318: mov      x1, x0
0207d31c: str      x1, [x19, #0x80]!
0207d320: mov      x0, x19
0207d324: ldp      x20, x19, [sp, #0x10]
0207d328: ldr      x30, [sp], #0x20
0207d32c: b        #0x18ddb68
0207d330: ldp      x20, x19, [sp, #0x10]
0207d334: ldr      x30, [sp], #0x20
0207d338: ret

; 0x207d33c FishFlock.FishFlockController$$UpdateCollisionData | void UpdateCollisionData()
0207d33c: stp      d15, d14, [sp, #-0xa0]!
0207d340: stp      d13, d12, [sp, #0x10]
0207d344: stp      d11, d10, [sp, #0x20]
0207d348: stp      d9, d8, [sp, #0x30]
0207d34c: stp      x29, x30, [sp, #0x40]
0207d350: stp      x28, x27, [sp, #0x50]
0207d354: stp      x26, x25, [sp, #0x60]
0207d358: stp      x24, x23, [sp, #0x70]
0207d35c: stp      x22, x21, [sp, #0x80]
0207d360: stp      x20, x19, [sp, #0x90]
0207d364: adrp     x20, #0x3ed5000
0207d368: ldrb     w8, [x20, #0x4ee]
0207d36c: mov      x19, x0
0207d370: tbnz     w8, #0, #0x207d3f4
0207d374: adrp     x0, #0x3c2c000
0207d378: ldr      x0, [x0, #0x7a8]
0207d37c: bl       #0x18ddbc4
0207d380: adrp     x0, #0x3bfc000
0207d384: ldr      x0, [x0, #0x850]
0207d388: bl       #0x18ddbc4
0207d38c: adrp     x0, #0x3c05000
0207d390: ldr      x0, [x0, #0x520]
0207d394: bl       #0x18ddbc4
0207d398: adrp     x0, #0x3c2c000
0207d39c: ldr      x0, [x0, #0x7b0]
0207d3a0: bl       #0x18ddbc4
0207d3a4: adrp     x0, #0x3bf7000
0207d3a8: ldr      x0, [x0, #0xcb0]
0207d3ac: bl       #0x18ddbc4
0207d3b0: adrp     x0, #0x3bf7000
0207d3b4: ldr      x0, [x0, #0x468]
0207d3b8: bl       #0x18ddbc4
0207d3bc: adrp     x0, #0x3bfc000
0207d3c0: ldr      x0, [x0, #0x860]
0207d3c4: bl       #0x18ddbc4
0207d3c8: adrp     x0, #0x3c13000
0207d3cc: ldr      x0, [x0, #0xea8]
0207d3d0: bl       #0x18ddbc4
0207d3d4: adrp     x0, #0x3bf7000
0207d3d8: ldr      x0, [x0, #0xca8]
0207d3dc: bl       #0x18ddbc4
0207d3e0: adrp     x0, #0x3c2c000
0207d3e4: ldr      x0, [x0, #0x7b8]
0207d3e8: bl       #0x18ddbc4
0207d3ec: mov      w8, #1
0207d3f0: strb     w8, [x20, #0x4ee]
0207d3f4: mov      x20, x19
0207d3f8: ldr      x8, [x20, #0x50]!
0207d3fc: cbz      x8, #0x207d704
0207d400: ldr      w21, [x8, #0x18]
0207d404: cmp      w21, #1
0207d408: b.lt     #0x207d704
0207d40c: mov      x22, x19
0207d410: ldr      x8, [x22, #0x60]!
0207d414: cbz      x8, #0x207d424
0207d418: ldr      w8, [x8, #0x18]
0207d41c: cmp      w21, w8
0207d420: b.eq     #0x207d448
0207d424: adrp     x8, #0x3c2c000
0207d428: ldr      x8, [x8, #0x7b0]
0207d42c: mov      w1, w21
0207d430: ldr      x0, [x8]
0207d434: bl       #0x18ddc6c
0207d438: mov      x1, x0
0207d43c: str      x0, [x22]
0207d440: mov      x0, x22
0207d444: bl       #0x18ddb68
0207d448: adrp     x27, #0x3bf7000
0207d44c: adrp     x29, #0x3bf7000
0207d450: ldr      x27, [x27, #0x468]
0207d454: ldr      x29, [x29, #0xca8]
0207d458: mov      w26, wzr
0207d45c: fmov     s14, #0.50000000
0207d460: ldr      x8, [x20]
0207d464: cbz      x8, #0x207d7a8
0207d468: ldr      w9, [x8, #0x18]
0207d46c: cmp      w26, w9
0207d470: b.hs     #0x207d7ac
0207d474: ldr      x0, [x27]
0207d478: sxtw     x28, w26
0207d47c: add      x8, x8, x28, lsl #3
0207d480: ldr      x23, [x8, #0x20]
0207d484: ldr      w9, [x0, #0xe0]
0207d488: cbnz     w9, #0x207d490
0207d48c: bl       #0x18ddcfc
0207d490: mov      x0, x23
0207d494: mov      x1, xzr
0207d498: mov      x2, xzr
0207d49c: bl       #0x39106d8 ; UnityEngine.Object$$op_Equality
0207d4a0: tbnz     w0, #0, #0x207d730
0207d4a4: cbz      x23, #0x207d7a8
0207d4a8: mov      x0, x23
0207d4ac: mov      x1, xzr
0207d4b0: bl       #0x30c71ec ; System.Object$$GetType
0207d4b4: ldr      x8, [x29]
0207d4b8: adrp     x10, #0x3bfc000
0207d4bc: mov      x24, x0
0207d4c0: ldr      w9, [x8, #0xe0]
0207d4c4: ldr      x10, [x10, #0x850]
0207d4c8: ldr      x25, [x10]
0207d4cc: cbnz     w9, #0x207d4d8
0207d4d0: mov      x0, x8
0207d4d4: bl       #0x18ddcfc
0207d4d8: mov      x0, x25
0207d4dc: mov      x1, xzr
0207d4e0: bl       #0x308f85c ; System.Type$$GetTypeFromHandle
0207d4e4: mov      x1, x0
0207d4e8: mov      x0, x24
0207d4ec: mov      x2, xzr
0207d4f0: bl       #0x3098b70 ; System.Type$$op_Equality
0207d4f4: tbz      w0, #0, #0x207d5d4
0207d4f8: adrp     x9, #0x3c05000
0207d4fc: ldr      x8, [x23]
0207d500: ldr      x9, [x9, #0x520]
0207d504: ldrb     w10, [x8, #0x130]
0207d508: ldr      x1, [x9]
0207d50c: ldrb     w9, [x1, #0x130]
0207d510: cmp      w10, w9
0207d514: b.lo     #0x207d7b0
0207d518: ldr      x8, [x8, #0xc8]
0207d51c: add      x8, x8, x9, lsl #3
0207d520: ldur     x8, [x8, #-8]
0207d524: cmp      x8, x1
0207d528: b.ne     #0x207d7b0
0207d52c: mov      x0, x23
0207d530: mov      x1, xzr
0207d534: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207d538: cbz      x0, #0x207d7a8
0207d53c: mov      x1, xzr
0207d540: bl       #0x391b760 ; UnityEngine.Transform$$get_localScale
0207d544: mov      x0, x23
0207d548: mov      x1, xzr
0207d54c: mov      v8.16b, v0.16b
0207d550: mov      v9.16b, v1.16b
0207d554: mov      v10.16b, v2.16b
0207d558: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207d55c: cbz      x0, #0x207d7a8
0207d560: mov      x1, xzr
0207d564: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207d568: mov      x0, x23
0207d56c: mov      x1, xzr
0207d570: mov      v11.16b, v0.16b
0207d574: mov      v12.16b, v1.16b
0207d578: mov      v13.16b, v2.16b
0207d57c: bl       #0x397eed8 ; UnityEngine.BoxCollider$$get_center
0207d580: mov      x0, x23
0207d584: mov      x1, xzr
0207d588: fadd     s11, s11, s0
0207d58c: fadd     s15, s12, s1
0207d590: fadd     s13, s13, s2
0207d594: bl       #0x397f010 ; UnityEngine.BoxCollider$$get_size
0207d598: ldr      s3, [x19, #0x4c]
0207d59c: fmul     s0, s8, s0
0207d5a0: fmul     s1, s9, s1
0207d5a4: fmul     s2, s10, s2
0207d5a8: fadd     s0, s3, s0
0207d5ac: fadd     s12, s3, s1
0207d5b0: fadd     s1, s3, s2
0207d5b4: fmul     s2, s0, s14
0207d5b8: fmul     s3, s12, s14
0207d5bc: fmul     s4, s1, s14
0207d5c0: mov      w8, wzr
0207d5c4: fsub     s8, s11, s2
0207d5c8: fsub     s9, s15, s3
0207d5cc: fsub     s10, s13, s4
0207d5d0: b        #0x207d6cc
0207d5d4: mov      x0, x23
0207d5d8: mov      x1, xzr
0207d5dc: bl       #0x30c71ec ; System.Object$$GetType
0207d5e0: ldr      x8, [x29]
0207d5e4: adrp     x10, #0x3bfc000
0207d5e8: mov      x24, x0
0207d5ec: ldr      w9, [x8, #0xe0]
0207d5f0: ldr      x10, [x10, #0x860]
0207d5f4: ldr      x25, [x10]
0207d5f8: cbnz     w9, #0x207d604
0207d5fc: mov      x0, x8
0207d600: bl       #0x18ddcfc
0207d604: mov      x0, x25
0207d608: mov      x1, xzr
0207d60c: bl       #0x308f85c ; System.Type$$GetTypeFromHandle
0207d610: mov      x1, x0
0207d614: mov      x0, x24
0207d618: mov      x2, xzr
0207d61c: bl       #0x3098b70 ; System.Type$$op_Equality
0207d620: fmov     s12, wzr
0207d624: tbz      w0, #0, #0x207d6b4
0207d628: adrp     x9, #0x3c13000
0207d62c: ldr      x8, [x23]
0207d630: ldr      x9, [x9, #0xea8]
0207d634: ldrb     w10, [x8, #0x130]
0207d638: ldr      x1, [x9]
0207d63c: ldrb     w9, [x1, #0x130]
0207d640: cmp      w10, w9
0207d644: b.lo     #0x207d7b0
0207d648: ldr      x8, [x8, #0xc8]
0207d64c: add      x8, x8, x9, lsl #3
0207d650: ldur     x8, [x8, #-8]
0207d654: cmp      x8, x1
0207d658: b.ne     #0x207d7b0
0207d65c: mov      x0, x23
0207d660: mov      x1, xzr
0207d664: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207d668: cbz      x0, #0x207d7a8
0207d66c: mov      x1, xzr
0207d670: bl       #0x391b760 ; UnityEngine.Transform$$get_localScale
0207d674: mov      x0, x23
0207d678: mov      x1, xzr
0207d67c: mov      v11.16b, v0.16b
0207d680: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207d684: cbz      x0, #0x207d7a8
0207d688: mov      x1, xzr
0207d68c: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207d690: mov      x0, x23
0207d694: mov      x1, xzr
0207d698: mov      v8.16b, v0.16b
0207d69c: mov      v9.16b, v1.16b
0207d6a0: mov      v10.16b, v2.16b
0207d6a4: bl       #0x397f288 ; UnityEngine.SphereCollider$$get_radius
0207d6a8: fmul     s0, s11, s0
0207d6ac: mov      w8, #1
0207d6b0: b        #0x207d6c8
0207d6b4: mov      w8, wzr
0207d6b8: fmov     s8, wzr
0207d6bc: fmov     s9, wzr
0207d6c0: fmov     s10, wzr
0207d6c4: fmov     s0, wzr
0207d6c8: fmov     s1, wzr
0207d6cc: ldr      x9, [x22]
0207d6d0: cbz      x9, #0x207d7a8
0207d6d4: ldr      w10, [x9, #0x18]
0207d6d8: cmp      w26, w10
0207d6dc: b.hs     #0x207d7ac
0207d6e0: mov      w10, #0x1c
0207d6e4: add      w26, w26, #1
0207d6e8: madd     x9, x28, x10, x9
0207d6ec: cmp      w21, w26
0207d6f0: stp      s8, s9, [x9, #0x20]
0207d6f4: stp      s10, s0, [x9, #0x28]
0207d6f8: stp      s12, s1, [x9, #0x30]
0207d6fc: str      w8, [x9, #0x38]
0207d700: b.ne     #0x207d460
0207d704: ldp      x20, x19, [sp, #0x90]
0207d708: ldp      x22, x21, [sp, #0x80]
0207d70c: ldp      x24, x23, [sp, #0x70]
0207d710: ldp      x26, x25, [sp, #0x60]
0207d714: ldp      x28, x27, [sp, #0x50]
0207d718: ldp      x29, x30, [sp, #0x40]
0207d71c: ldp      d9, d8, [sp, #0x30]
0207d720: ldp      d11, d10, [sp, #0x20]
0207d724: ldp      d13, d12, [sp, #0x10]
0207d728: ldp      d15, d14, [sp], #0xa0
0207d72c: ret
0207d730: adrp     x8, #0x3bf7000
0207d734: ldr      x8, [x8, #0xcb0]
0207d738: ldr      x0, [x8]
0207d73c: ldr      w8, [x0, #0xe0]
0207d740: cbnz     w8, #0x207d748
0207d744: bl       #0x18ddcfc
0207d748: adrp     x8, #0x3c2c000
0207d74c: ldr      x8, [x8, #0x7b8]
0207d750: mov      x1, xzr
0207d754: ldr      x0, [x8]
0207d758: bl       #0x38d3a94 ; UnityEngine.Debug$$LogError
0207d75c: adrp     x8, #0x3c2c000
0207d760: ldr      x8, [x8, #0x7a8]
0207d764: mov      w1, wzr
0207d768: ldr      x0, [x8]
0207d76c: bl       #0x18ddc6c
0207d770: mov      x1, x0
0207d774: str      x0, [x20]
0207d778: mov      x0, x20
0207d77c: ldp      x20, x19, [sp, #0x90]
0207d780: ldp      x22, x21, [sp, #0x80]
0207d784: ldp      x24, x23, [sp, #0x70]
0207d788: ldp      x26, x25, [sp, #0x60]
0207d78c: ldp      x28, x27, [sp, #0x50]
0207d790: ldp      x29, x30, [sp, #0x40]
0207d794: ldp      d9, d8, [sp, #0x30]
0207d798: ldp      d11, d10, [sp, #0x20]
0207d79c: ldp      d13, d12, [sp, #0x10]
0207d7a0: ldp      d15, d14, [sp], #0xa0
0207d7a4: b        #0x18ddb68
0207d7a8: bl       #0x18dde20
0207d7ac: bl       #0x18dde28
0207d7b0: mov      x0, x23
0207d7b4: bl       #0x18de19c

; 0x207d7b8 FishFlock.FishFlockController$$CreateCollisionData | void CreateCollisionData()
0207d7b8: str      x30, [sp, #-0x20]!
0207d7bc: stp      x20, x19, [sp, #0x10]
0207d7c0: adrp     x20, #0x3ed5000
0207d7c4: ldrb     w8, [x20, #0x4ef]
0207d7c8: mov      x19, x0
0207d7cc: tbnz     w8, #0, #0x207d7e4
0207d7d0: adrp     x0, #0x3c2c000
0207d7d4: ldr      x0, [x0, #0x7b0]
0207d7d8: bl       #0x18ddbc4
0207d7dc: mov      w8, #1
0207d7e0: strb     w8, [x20, #0x4ef]
0207d7e4: ldr      x8, [x19, #0x50]
0207d7e8: cbz      x8, #0x207d848
0207d7ec: ldr      x9, [x8, #0x18]
0207d7f0: cbnz     x9, #0x207d824
0207d7f4: adrp     x8, #0x3c2c000
0207d7f8: ldr      x8, [x8, #0x7b0]
0207d7fc: mov      w1, #1
0207d800: ldr      x0, [x8]
0207d804: bl       #0x18ddc6c
0207d808: mov      x20, x19
0207d80c: str      x0, [x20, #0x60]!
0207d810: mov      x1, x0
0207d814: mov      x0, x20
0207d818: bl       #0x18ddb68
0207d81c: ldur     x8, [x20, #-0x10]
0207d820: cbz      x8, #0x207d848
0207d824: ldr      x8, [x8, #0x18]
0207d828: cbz      x8, #0x207d838
0207d82c: ldr      x8, [x19, #0x60]
0207d830: cbz      x8, #0x207d848
0207d834: ldr      w8, [x8, #0x18]
0207d838: str      w8, [x19, #0x68]
0207d83c: ldp      x20, x19, [sp, #0x10]
0207d840: ldr      x30, [sp], #0x20
0207d844: ret
0207d848: bl       #0x18dde20

; 0x207de90 FishFlock.FishFlockController$$Flee | Vector3 Flee(FishData data, Vector3 positionToEvade)
0207de90: stp      d13, d12, [sp, #-0x50]!
0207de94: stp      d11, d10, [sp, #0x10]
0207de98: stp      d9, d8, [sp, #0x20]
0207de9c: str      x30, [sp, #0x30]
0207dea0: stp      x20, x19, [sp, #0x40]
0207dea4: adrp     x20, #0x3ed3000
0207dea8: ldp      s11, s12, [x1]
0207deac: ldrb     w8, [x20, #0xb61]
0207deb0: ldr      s13, [x1, #8]
0207deb4: mov      v8.16b, v2.16b
0207deb8: mov      v9.16b, v1.16b
0207debc: mov      x19, x1
0207dec0: mov      v10.16b, v0.16b
0207dec4: cbnz     w8, #0x207dedc
0207dec8: adrp     x0, #0x3bf8000
0207decc: ldr      x0, [x0, #0xc80]
0207ded0: bl       #0x18ddbc4
0207ded4: mov      w8, #1
0207ded8: strb     w8, [x20, #0xb61]
0207dedc: adrp     x8, #0x3bf8000
0207dee0: ldr      x8, [x8, #0xc80]
0207dee4: fsub     s10, s11, s10
0207dee8: fsub     s9, s12, s9
0207deec: fsub     s8, s13, s8
0207def0: ldr      x0, [x8]
0207def4: ldr      w8, [x0, #0xe0]
0207def8: cbnz     w8, #0x207df00
0207defc: bl       #0x18ddcfc
0207df00: fmul     s0, s10, s10
0207df04: fmul     s1, s9, s9
0207df08: adrp     x8, #0x980000
0207df0c: fadd     s0, s0, s1
0207df10: ldr      s1, [x8, #0x764]
0207df14: fmul     s2, s8, s8
0207df18: fadd     s0, s2, s0
0207df1c: fsqrt    s2, s0
0207df20: fcmp     s2, s1
0207df24: b.le     #0x207df38
0207df28: fdiv     s0, s10, s2
0207df2c: fdiv     s1, s9, s2
0207df30: fdiv     s2, s8, s2
0207df34: b        #0x207df70
0207df38: adrp     x20, #0x3ed1000
0207df3c: ldrb     w8, [x20, #0x995]
0207df40: cbnz     w8, #0x207df58
0207df44: adrp     x0, #0x3bf7000
0207df48: ldr      x0, [x0, #0x380]
0207df4c: bl       #0x18ddbc4
0207df50: mov      w8, #1
0207df54: strb     w8, [x20, #0x995]
0207df58: adrp     x8, #0x3bf7000
0207df5c: ldr      x8, [x8, #0x380]
0207df60: ldr      x8, [x8]
0207df64: ldr      x8, [x8, #0xb8]
0207df68: ldp      s0, s1, [x8]
0207df6c: ldr      s2, [x8, #8]
0207df70: ldp      s6, s3, [x19, #0x14]
0207df74: ldp      s4, s5, [x19, #0xc]
0207df78: ldp      x20, x19, [sp, #0x40]
0207df7c: ldr      x30, [sp, #0x30]
0207df80: ldp      d9, d8, [sp, #0x20]
0207df84: ldp      d11, d10, [sp, #0x10]
0207df88: fmul     s0, s0, s3
0207df8c: fmul     s1, s1, s3
0207df90: fmul     s2, s2, s3
0207df94: fsub     s0, s0, s4
0207df98: fsub     s1, s1, s5
0207df9c: fsub     s2, s2, s6
0207dfa0: ldp      d13, d12, [sp], #0x50
0207dfa4: ret

; 0x207dfa8 FishFlock.FishFlockController$$ComputeFlockBehaviours | void ComputeFlockBehaviours()
0207dfa8: sub      sp, sp, #0x1c0
0207dfac: stp      d15, d14, [sp, #0x120]
0207dfb0: stp      d13, d12, [sp, #0x130]
0207dfb4: stp      d11, d10, [sp, #0x140]
0207dfb8: stp      d9, d8, [sp, #0x150]
0207dfbc: stp      x29, x30, [sp, #0x160]
0207dfc0: stp      x28, x27, [sp, #0x170]
0207dfc4: stp      x26, x25, [sp, #0x180]
0207dfc8: stp      x24, x23, [sp, #0x190]
0207dfcc: stp      x22, x21, [sp, #0x1a0]
0207dfd0: stp      x20, x19, [sp, #0x1b0]
0207dfd4: mrs      x8, tpidr_el0
0207dfd8: str      x8, [sp, #0x10]
0207dfdc: ldr      x8, [x8, #0x28]
0207dfe0: adrp     x19, #0x3ed5000
0207dfe4: mov      x27, x0
0207dfe8: str      x8, [sp, #0x118]
0207dfec: ldrb     w8, [x19, #0x4f0]
0207dff0: tbnz     w8, #0, #0x207e068
0207dff4: adrp     x0, #0x3bf8000
0207dff8: ldr      x0, [x0, #0x258]
0207dffc: bl       #0x18ddbc4
0207e000: adrp     x0, #0x3bfe000
0207e004: ldr      x0, [x0, #0xe40]
0207e008: bl       #0x18ddbc4
0207e00c: adrp     x0, #0x3c2c000
0207e010: ldr      x0, [x0, #0x710]
0207e014: bl       #0x18ddbc4
0207e018: adrp     x0, #0x3c2c000
0207e01c: ldr      x0, [x0, #0x790]
0207e020: bl       #0x18ddbc4
0207e024: adrp     x0, #0x3bf8000
0207e028: ldr      x0, [x0, #0x6d0]
0207e02c: bl       #0x18ddbc4
0207e030: adrp     x0, #0x3c2c000
0207e034: ldr      x0, [x0, #0x798]
0207e038: bl       #0x18ddbc4
0207e03c: adrp     x0, #0x3c2c000
0207e040: ldr      x0, [x0, #0x718]
0207e044: bl       #0x18ddbc4
0207e048: adrp     x0, #0x3bf8000
0207e04c: ldr      x0, [x0, #0x6d8]
0207e050: bl       #0x18ddbc4
0207e054: adrp     x0, #0x3c2c000
0207e058: ldr      x0, [x0, #0x720]
0207e05c: bl       #0x18ddbc4
0207e060: mov      w8, #1
0207e064: strb     w8, [x19, #0x4f0]
0207e068: ldr      x0, [x27, #0x88]
0207e06c: cbz      x0, #0x207ed80
0207e070: ldr      w8, [x0, #0x18]
0207e074: cbz      w8, #0x207ed80
0207e078: cmp      w8, #1
0207e07c: b.lt     #0x207ed80
0207e080: adrp     x21, #0x3c2c000
0207e084: adrp     x22, #0x3bf8000
0207e088: ldr      x21, [x21, #0x718]
0207e08c: ldr      x22, [x22, #0xc80]
0207e090: add      x8, sp, #0xc0
0207e094: add      x9, sp, #0x88
0207e098: mov      w20, wzr
0207e09c: add      x19, sp, #0x108
0207e0a0: adrp     x23, #0x3ed3000
0207e0a4: add      x25, x8, #0x29
0207e0a8: add      x28, x9, #0x29
0207e0ac: str      x27, [sp, #0x60]
0207e0b0: str      x25, [sp, #0x18]
0207e0b4: adrp     x8, #0x3c2c000
0207e0b8: ldr      x8, [x8, #0x798]
0207e0bc: ldr      x2, [x8]
0207e0c0: mov      w1, w20
0207e0c4: bl       #0x281fec4 ; System.Collections.Generic.List<object>$$get_Item
0207e0c8: mov      x10, x0
0207e0cc: cbz      x0, #0x207ec7c
0207e0d0: ldrb     w8, [x10, #0x25]
0207e0d4: cbz      w8, #0x207ec2c
0207e0d8: ldr      x8, [x27, #0x90]
0207e0dc: cbz      x8, #0x207ec84
0207e0e0: ldr      w9, [x8, #0x1c]
0207e0e4: add      w9, w9, #1
0207e0e8: stp      wzr, w9, [x8, #0x18]
0207e0ec: ldr      x9, [x10, #0x60]
0207e0f0: cbz      x9, #0x207ec74
0207e0f4: mov      w11, wzr
0207e0f8: str      x10, [sp, #0x48]
0207e0fc: ldr      w8, [x9, #0x18]
0207e100: cmp      w11, w8
0207e104: b.ge     #0x207ec2c
0207e108: ldr      x2, [x21]
0207e10c: add      x8, sp, #0xc0
0207e110: mov      x0, x9
0207e114: mov      w1, w11
0207e118: str      w11, [sp, #0x6c]
0207e11c: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207e120: ldr      s0, [sp, #0xd8]
0207e124: ldp      s1, s15, [sp, #0xc0]
0207e128: ldp      s11, s8, [sp, #0xc8]
0207e12c: ldp      s9, s10, [sp, #0xd0]
0207e130: str      s0, [sp, #0x7c]
0207e134: ldr      s0, [sp, #0xdc]
0207e138: ldrb     w29, [sp, #0xe8]
0207e13c: ldr      x8, [x25]
0207e140: ldur     x9, [x25, #7]
0207e144: ldr      x24, [sp, #0xe0]
0207e148: stp      s0, s1, [sp, #0x80]
0207e14c: str      x8, [sp, #0x108]
0207e150: stur     x9, [x19, #7]
0207e154: tbz      w29, #0, #0x207ec14
0207e158: ldr      w8, [x27, #0x30]
0207e15c: cmp      w8, #1
0207e160: b.eq     #0x207e174
0207e164: cmp      w8, #2
0207e168: b.ne     #0x207e178
0207e16c: fmov     s15, wzr
0207e170: b        #0x207e178
0207e174: fmov     s11, wzr
0207e178: adrp     x8, #0x3ed1000
0207e17c: ldrb     w8, [x8, #0x995]
0207e180: cbnz     w8, #0x207e19c
0207e184: adrp     x0, #0x3bf7000
0207e188: ldr      x0, [x0, #0x380]
0207e18c: bl       #0x18ddbc4
0207e190: adrp     x8, #0x3ed1000
0207e194: mov      w9, #1
0207e198: strb     w9, [x8, #0x995]
0207e19c: stp      s10, s9, [sp, #0x70]
0207e1a0: str      s8, [sp, #0x78]
0207e1a4: adrp     x8, #0x3bf7000
0207e1a8: ldr      x8, [x8, #0x380]
0207e1ac: ldr      x10, [sp, #0x48]
0207e1b0: ldr      w9, [x27, #0x68]
0207e1b4: ldr      x8, [x8]
0207e1b8: ldp      s14, s13, [x10, #0x94]
0207e1bc: ldr      s8, [x10, #0x9c]
0207e1c0: cmp      w9, #1
0207e1c4: ldr      x8, [x8, #0xb8]
0207e1c8: ldr      s1, [x8]
0207e1cc: ldr      s0, [x8, #4]
0207e1d0: stp      s0, s1, [sp, #0x58]
0207e1d4: ldr      s0, [x8, #8]
0207e1d8: str      s0, [sp, #0x54]
0207e1dc: b.lt     #0x207e4e0
0207e1e0: fmov     s2, wzr
0207e1e4: str      s2, [sp, #0x2c]
0207e1e8: fmov     s2, wzr
0207e1ec: ldr      s1, [x27, #0x78]
0207e1f0: str      s2, [sp, #0x34]
0207e1f4: ldr      s2, [sp, #0x7c]
0207e1f8: ldr      s0, [x27, #0x44]
0207e1fc: ldr      s4, [sp, #0x70]
0207e200: mov      x19, xzr
0207e204: fmul     s1, s2, s1
0207e208: ldp      s3, s2, [sp, #0x74]
0207e20c: scvtf    s0, s0
0207e210: mov      x25, xzr
0207e214: str      s14, [sp, #0x44]
0207e218: fmul     s2, s2, s0
0207e21c: fmul     s3, s3, s0
0207e220: fmul     s0, s4, s0
0207e224: fmul     s2, s2, s1
0207e228: fmul     s3, s3, s1
0207e22c: fmul     s0, s0, s1
0207e230: ldr      s1, [sp, #0x84]
0207e234: fadd     s0, s11, s0
0207e238: str      s0, [sp, #0x38]
0207e23c: fmov     s0, wzr
0207e240: fadd     s4, s1, s2
0207e244: fadd     s1, s15, s3
0207e248: stp      s1, s4, [sp, #0x3c]
0207e24c: str      s0, [sp, #0x30]
0207e250: ldr      x8, [x27, #0x60]
0207e254: cbz      x8, #0x207ec68
0207e258: ldr      w9, [x8, #0x18]
0207e25c: cmp      x25, x9
0207e260: b.hs     #0x207ec64
0207e264: add      x8, x8, x19
0207e268: ldp      s10, s14, [x8, #0x20]
0207e26c: ldr      w9, [x8, #0x38]
0207e270: ldp      s12, s9, [x8, #0x28]
0207e274: cbz      w9, #0x207e338
0207e278: cmp      w9, #1
0207e27c: b.ne     #0x207e344
0207e280: ldr      s0, [sp, #0x40]
0207e284: fsub     s10, s0, s10
0207e288: ldr      s0, [sp, #0x3c]
0207e28c: fsub     s14, s0, s14
0207e290: ldr      s0, [sp, #0x38]
0207e294: fmul     s1, s14, s14
0207e298: fsub     s12, s0, s12
0207e29c: fmul     s0, s10, s10
0207e2a0: fadd     s0, s0, s1
0207e2a4: fmul     s1, s12, s12
0207e2a8: fadd     s0, s1, s0
0207e2ac: fsqrt    s0, s0
0207e2b0: fcmp     s0, s9
0207e2b4: b.hi     #0x207e344
0207e2b8: adrp     x8, #0x3ed3000
0207e2bc: ldrb     w8, [x8, #0xb61]
0207e2c0: cbnz     w8, #0x207e2d8
0207e2c4: mov      x0, x22
0207e2c8: bl       #0x18ddbc4
0207e2cc: mov      w8, #1
0207e2d0: adrp     x9, #0x3ed3000
0207e2d4: strb     w8, [x9, #0xb61]
0207e2d8: ldr      x0, [x22]
0207e2dc: ldr      w8, [x0, #0xe0]
0207e2e0: cbnz     w8, #0x207e2e8
0207e2e4: bl       #0x18ddcfc
0207e2e8: ldp      s0, s1, [sp, #0x30]
0207e2ec: ldr      s2, [sp, #0x2c]
0207e2f0: adrp     x8, #0x980000
0207e2f4: ldr      s4, [x8, #0x764]
0207e2f8: fadd     s0, s0, s10
0207e2fc: fadd     s1, s1, s14
0207e300: fadd     s2, s2, s12
0207e304: fmul     s3, s0, s0
0207e308: fmul     s5, s1, s1
0207e30c: fadd     s3, s3, s5
0207e310: fmul     s5, s2, s2
0207e314: fadd     s3, s5, s3
0207e318: fsqrt    s3, s3
0207e31c: fcmp     s3, s4
0207e320: b.le     #0x207e46c
0207e324: ldr      s14, [sp, #0x44]
0207e328: fdiv     s0, s0, s3
0207e32c: fdiv     s1, s1, s3
0207e330: fdiv     s2, s2, s3
0207e334: b        #0x207e4b0
0207e338: ldr      s0, [sp, #0x40]
0207e33c: fcmp     s0, s10
0207e340: b.ge     #0x207e34c
0207e344: ldr      s14, [sp, #0x44]
0207e348: b        #0x207e4c8
0207e34c: ldr      s0, [sp, #0x3c]
0207e350: fcmp     s0, s14
0207e354: b.lt     #0x207e344
0207e358: ldr      s1, [sp, #0x40]
0207e35c: fadd     s0, s10, s9
0207e360: fcmp     s1, s0
0207e364: b.hi     #0x207e344
0207e368: ldr      s0, [sp, #0x38]
0207e36c: fcmp     s0, s12
0207e370: b.lt     #0x207e344
0207e374: ldr      s0, [x8, #0x30]
0207e378: ldr      s1, [sp, #0x3c]
0207e37c: str      s0, [sp, #0x28]
0207e380: fadd     s0, s14, s0
0207e384: fcmp     s1, s0
0207e388: b.hi     #0x207e344
0207e38c: ldr      s0, [x8, #0x34]
0207e390: ldr      s1, [sp, #0x38]
0207e394: str      s0, [sp, #0x24]
0207e398: fadd     s0, s12, s0
0207e39c: fcmp     s1, s0
0207e3a0: b.hi     #0x207e344
0207e3a4: adrp     x8, #0x3ed3000
0207e3a8: ldrb     w8, [x8, #0xb61]
0207e3ac: cbnz     w8, #0x207e3c4
0207e3b0: mov      x0, x22
0207e3b4: bl       #0x18ddbc4
0207e3b8: mov      w8, #1
0207e3bc: adrp     x9, #0x3ed3000
0207e3c0: strb     w8, [x9, #0xb61]
0207e3c4: ldr      x0, [x22]
0207e3c8: ldr      w8, [x0, #0xe0]
0207e3cc: cbnz     w8, #0x207e3d4
0207e3d0: bl       #0x18ddcfc
0207e3d4: ldp      s3, s1, [sp, #0x24]
0207e3d8: fmov     s2, #0.50000000
0207e3dc: fmul     s0, s9, s2
0207e3e0: fadd     s0, s10, s0
0207e3e4: fmul     s1, s1, s2
0207e3e8: fmul     s2, s3, s2
0207e3ec: ldr      s3, [sp, #0x40]
0207e3f0: fadd     s1, s14, s1
0207e3f4: fadd     s2, s12, s2
0207e3f8: adrp     x8, #0x980000
0207e3fc: fsub     s0, s3, s0
0207e400: ldr      s3, [sp, #0x3c]
0207e404: ldr      s4, [x8, #0x764]
0207e408: fsub     s1, s3, s1
0207e40c: ldr      s3, [sp, #0x38]
0207e410: fsub     s2, s3, s2
0207e414: ldr      s3, [sp, #0x30]
0207e418: fadd     s0, s3, s0
0207e41c: ldr      s3, [sp, #0x34]
0207e420: fadd     s1, s3, s1
0207e424: ldr      s3, [sp, #0x2c]
0207e428: fmul     s5, s1, s1
0207e42c: fadd     s2, s3, s2
0207e430: fmul     s3, s0, s0
0207e434: fadd     s3, s3, s5
0207e438: fmul     s5, s2, s2
0207e43c: fadd     s3, s5, s3
0207e440: fsqrt    s3, s3
0207e444: fcmp     s3, s4
0207e448: b.gt     #0x207e324
0207e44c: adrp     x8, #0x3ed1000
0207e450: ldrb     w8, [x8, #0x995]
0207e454: ldr      s14, [sp, #0x44]
0207e458: cbnz     w8, #0x207e498
0207e45c: adrp     x0, #0x3bf7000
0207e460: ldr      x0, [x0, #0x380]
0207e464: bl       #0x18ddbc4
0207e468: b        #0x207e488
0207e46c: adrp     x8, #0x3ed1000
0207e470: ldrb     w8, [x8, #0x995]
0207e474: ldr      s14, [sp, #0x44]
0207e478: cbnz     w8, #0x207e498
0207e47c: adrp     x0, #0x3bf7000
0207e480: ldr      x0, [x0, #0x380]
0207e484: bl       #0x18ddbc4
0207e488: ldr      s14, [sp, #0x44]
0207e48c: adrp     x8, #0x3ed1000
0207e490: mov      w9, #1
0207e494: strb     w9, [x8, #0x995]
0207e498: adrp     x8, #0x3bf7000
0207e49c: ldr      x8, [x8, #0x380]
0207e4a0: ldr      x8, [x8]
0207e4a4: ldr      x8, [x8, #0xb8]
0207e4a8: ldp      s0, s1, [x8]
0207e4ac: ldr      s2, [x8, #8]
0207e4b0: ldr      s3, [x27, #0x48]
0207e4b4: fmul     s4, s0, s3
0207e4b8: fmul     s0, s1, s3
0207e4bc: stp      s4, s0, [sp, #0x30]
0207e4c0: fmul     s0, s2, s3
0207e4c4: str      s0, [sp, #0x2c]
0207e4c8: ldrsw    x8, [x27, #0x68]
0207e4cc: add      x25, x25, #1
0207e4d0: add      x19, x19, #0x1c
0207e4d4: cmp      x25, x8
0207e4d8: b.lt     #0x207e250
0207e4dc: b        #0x207e4f8
0207e4e0: fmov     s0, wzr
0207e4e4: str      s0, [sp, #0x30]
0207e4e8: fmov     s0, wzr
0207e4ec: str      s0, [sp, #0x34]
0207e4f0: fmov     s0, wzr
0207e4f4: str      s0, [sp, #0x2c]
0207e4f8: ldr      x8, [x27, #0x88]
0207e4fc: cbz      x8, #0x207ec50
0207e500: ldp      s12, s9, [sp, #0x58]
0207e504: ldr      s10, [sp, #0x54]
0207e508: mov      w25, wzr
0207e50c: mov      w19, #1
0207e510: ldr      w9, [x8, #0x18]
0207e514: cmp      w25, w9
0207e518: b.ge     #0x207e6f0
0207e51c: adrp     x9, #0x3c2c000
0207e520: ldr      x9, [x9, #0x798]
0207e524: ldr      x2, [x9]
0207e528: mov      x0, x8
0207e52c: mov      w1, w25
0207e530: bl       #0x281fec4 ; System.Collections.Generic.List<object>$$get_Item
0207e534: mov      x26, x0
0207e538: cbz      x0, #0x207ec58
0207e53c: ldr      x10, [sp, #0x48]
0207e540: ldr      w9, [x26, #0x38]
0207e544: ldr      w8, [x10, #0x38]
0207e548: cmp      w8, w9
0207e54c: b.ne     #0x207e678
0207e550: ldr      s0, [x26, #0x48]
0207e554: ldr      s1, [x10, #0x48]
0207e558: mov      w9, #0x7f800000
0207e55c: fmov     w8, s0
0207e560: and      w8, w8, #0x7fffffff
0207e564: cmp      w8, w9
0207e568: fccmp    s1, s0, #0, ls
0207e56c: fcsel    s0, s1, s0, gt
0207e570: str      s0, [x27, #0x40]
0207e574: ldr      x0, [x26, #0x60]
0207e578: cbz      x0, #0x207ec4c
0207e57c: mov      w27, wzr
0207e580: ldr      w8, [x0, #0x18]
0207e584: cmp      w27, w8
0207e588: b.ge     #0x207e6dc
0207e58c: cmp      w25, w20
0207e590: b.ne     #0x207e5a0
0207e594: ldr      w8, [sp, #0x6c]
0207e598: cmp      w8, w27
0207e59c: b.eq     #0x207e668
0207e5a0: ldr      x2, [x21]
0207e5a4: add      x8, sp, #0xc0
0207e5a8: mov      w1, w27
0207e5ac: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207e5b0: ldp      s1, s2, [sp, #0xc0]
0207e5b4: ldr      s3, [sp, #0x84]
0207e5b8: ldr      s0, [sp, #0xc8]
0207e5bc: ldr      x8, [sp, #0x60]
0207e5c0: fsub     s4, s15, s2
0207e5c4: fsub     s3, s3, s1
0207e5c8: fsub     s5, s11, s0
0207e5cc: ldr      s7, [x8, #0x40]
0207e5d0: fmul     s6, s3, s3
0207e5d4: fmul     s16, s4, s4
0207e5d8: fadd     s6, s6, s16
0207e5dc: fmul     s16, s5, s5
0207e5e0: fadd     s6, s16, s6
0207e5e4: fsqrt    s6, s6
0207e5e8: fcmp     s6, s7
0207e5ec: b.pl     #0x207e668
0207e5f0: fdiv     s7, s6, s7
0207e5f4: fadd     s13, s13, s2
0207e5f8: fmov     s2, #1.00000000
0207e5fc: fadd     s14, s14, s1
0207e600: fsub     s1, s2, s7
0207e604: fmin     s2, s1, s2
0207e608: fcmp     s1, #0.0
0207e60c: fmov     s1, wzr
0207e610: fcsel    s1, s2, s1, pl
0207e614: fdiv     s1, s1, s6
0207e618: fmul     s2, s3, s1
0207e61c: fmul     s3, s4, s1
0207e620: ldr      s4, [sp, #0x5c]
0207e624: ldp      s16, s17, [sp, #0xcc]
0207e628: ldr      s18, [sp, #0xd4]
0207e62c: add      w19, w19, #1
0207e630: fadd     s4, s4, s2
0207e634: ldr      s2, [sp, #0x58]
0207e638: fmul     s1, s5, s1
0207e63c: cmp      w19, #9
0207e640: fadd     s9, s9, s16
0207e644: fadd     s2, s2, s3
0207e648: stp      s2, s4, [sp, #0x58]
0207e64c: ldr      s2, [sp, #0x54]
0207e650: fadd     s12, s12, s17
0207e654: fadd     s10, s10, s18
0207e658: fadd     s8, s8, s0
0207e65c: fadd     s2, s2, s1
0207e660: str      s2, [sp, #0x54]
0207e664: b.gt     #0x207e6dc
0207e668: ldr      x0, [x26, #0x60]
0207e66c: add      w27, w27, #1
0207e670: cbnz     x0, #0x207e580
0207e674: b        #0x207ec4c
0207e678: b.ge     #0x207e6dc
0207e67c: ldr      x0, [x27, #0x90]
0207e680: cbz      x0, #0x207ec6c
0207e684: adrp     x9, #0x3bf8000
0207e688: ldr      w10, [x0, #0x1c]
0207e68c: ldr      x8, [x0, #0x10]
0207e690: ldr      x9, [x9, #0x258]
0207e694: add      w10, w10, #1
0207e698: ldr      x9, [x9]
0207e69c: str      w10, [x0, #0x1c]
0207e6a0: cbz      x8, #0x207ec70
0207e6a4: ldrsw    x10, [x0, #0x18]
0207e6a8: ldr      w11, [x8, #0x18]
0207e6ac: cmp      w10, w11
0207e6b0: b.hs     #0x207e6c8
0207e6b4: add      w9, w10, #1
0207e6b8: add      x8, x8, x10, lsl #2
0207e6bc: str      w9, [x0, #0x18]
0207e6c0: str      w25, [x8, #0x20]
0207e6c4: b        #0x207e6dc
0207e6c8: ldr      x8, [x9, #0x20]
0207e6cc: ldr      x8, [x8, #0xc0]
0207e6d0: ldr      x2, [x8, #0x70]
0207e6d4: mov      w1, w25
0207e6d8: bl       #0x2808424 ; System.Collections.Generic.List<int>$$AddWithResize
0207e6dc: ldr      x27, [sp, #0x60]
0207e6e0: add      w25, w25, #1
0207e6e4: ldr      x8, [x27, #0x88]
0207e6e8: cbnz     x8, #0x207e510
0207e6ec: b        #0x207ec50
0207e6f0: adrp     x8, #0x3ed3000
0207e6f4: ldrb     w8, [x8, #0xb61]
0207e6f8: cbnz     w8, #0x207e710
0207e6fc: mov      x0, x22
0207e700: bl       #0x18ddbc4
0207e704: mov      w8, #1
0207e708: adrp     x9, #0x3ed3000
0207e70c: strb     w8, [x9, #0xb61]
0207e710: ldr      x0, [x22]
0207e714: ldr      w8, [x0, #0xe0]
0207e718: cbnz     w8, #0x207e720
0207e71c: bl       #0x18ddcfc
0207e720: ldr      s3, [sp, #0x84]
0207e724: scvtf    s0, w19
0207e728: fmov     s1, #1.00000000
0207e72c: mov      v2.16b, v14.16b
0207e730: fdiv     s14, s1, s0
0207e734: fmul     s0, s14, s2
0207e738: fmul     s1, s13, s14
0207e73c: adrp     x8, #0x980000
0207e740: fmul     s2, s8, s14
0207e744: fsub     s0, s0, s3
0207e748: fsub     s1, s1, s15
0207e74c: ldr      s5, [x8, #0x764]
0207e750: fsub     s2, s2, s11
0207e754: fmul     s3, s0, s0
0207e758: fmul     s4, s1, s1
0207e75c: fadd     s3, s4, s3
0207e760: fmul     s4, s2, s2
0207e764: fadd     s3, s4, s3
0207e768: fsqrt    s3, s3
0207e76c: fcmp     s3, s5
0207e770: str      s5, [sp, #0x44]
0207e774: b.le     #0x207e78c
0207e778: fdiv     s8, s0, s3
0207e77c: fdiv     s1, s1, s3
0207e780: fdiv     s0, s2, s3
0207e784: add      x19, sp, #0x108
0207e788: b        #0x207e7d0
0207e78c: adrp     x8, #0x3ed1000
0207e790: ldrb     w8, [x8, #0x995]
0207e794: add      x19, sp, #0x108
0207e798: cbnz     w8, #0x207e7b8
0207e79c: adrp     x0, #0x3bf7000
0207e7a0: ldr      x0, [x0, #0x380]
0207e7a4: bl       #0x18ddbc4
0207e7a8: adrp     x8, #0x3ed1000
0207e7ac: mov      w9, #1
0207e7b0: add      x19, sp, #0x108
0207e7b4: strb     w9, [x8, #0x995]
0207e7b8: adrp     x8, #0x3bf7000
0207e7bc: ldr      x8, [x8, #0x380]
0207e7c0: ldr      x8, [x8]
0207e7c4: ldr      x8, [x8, #0xb8]
0207e7c8: ldp      s8, s1, [x8]
0207e7cc: ldr      s0, [x8, #8]
0207e7d0: ldr      s3, [sp, #0x58]
0207e7d4: fmul     s2, s14, s12
0207e7d8: ldr      w8, [x27, #0x30]
0207e7dc: fadd     s2, s2, s3
0207e7e0: fadd     s1, s2, s1
0207e7e4: ldr      s2, [sp, #0x34]
0207e7e8: cmp      w8, #1
0207e7ec: fadd     s12, s2, s1
0207e7f0: b.eq     #0x207e81c
0207e7f4: ldr      s2, [sp, #0x54]
0207e7f8: fmul     s1, s14, s10
0207e7fc: cmp      w8, #2
0207e800: fadd     s1, s1, s2
0207e804: fadd     s0, s1, s0
0207e808: ldr      s1, [sp, #0x2c]
0207e80c: fadd     s10, s1, s0
0207e810: b.ne     #0x207e820
0207e814: fmov     s12, wzr
0207e818: b        #0x207e820
0207e81c: fmov     s10, wzr
0207e820: adrp     x8, #0x3ed1000
0207e824: ldrb     w8, [x8, #0x995]
0207e828: cbnz     w8, #0x207e844
0207e82c: adrp     x0, #0x3bf7000
0207e830: ldr      x0, [x0, #0x380]
0207e834: bl       #0x18ddbc4
0207e838: adrp     x8, #0x3ed1000
0207e83c: mov      w9, #1
0207e840: strb     w9, [x8, #0x995]
0207e844: ldr      x8, [x27, #0x90]
0207e848: stp      s10, s12, [sp, #0x54]
0207e84c: cbz      x8, #0x207ec54
0207e850: adrp     x9, #0x3bf7000
0207e854: ldr      x9, [x9, #0x380]
0207e858: ldr      s1, [sp, #0x5c]
0207e85c: fmul     s0, s14, s9
0207e860: mov      w25, wzr
0207e864: ldr      x9, [x9]
0207e868: fadd     s0, s0, s1
0207e86c: ldr      s1, [sp, #0x30]
0207e870: fadd     s0, s0, s8
0207e874: ldr      x9, [x9, #0xb8]
0207e878: fadd     s0, s1, s0
0207e87c: str      s0, [sp, #0x5c]
0207e880: ldp      s12, s13, [x9, #4]
0207e884: ldr      s14, [x9]
0207e888: ldr      w9, [x8, #0x18]
0207e88c: cmp      w25, w9
0207e890: b.ge     #0x207e9e0
0207e894: adrp     x9, #0x3bf8000
0207e898: ldr      x9, [x9, #0x6d8]
0207e89c: ldr      x2, [x9]
0207e8a0: mov      x0, x8
0207e8a4: mov      w1, w25
0207e8a8: bl       #0x2808134 ; System.Collections.Generic.List<int>$$get_Item
0207e8ac: mov      w1, w0
0207e8b0: ldr      x0, [x27, #0x88]
0207e8b4: cbz      x0, #0x207ec60
0207e8b8: adrp     x8, #0x3c2c000
0207e8bc: ldr      x8, [x8, #0x798]
0207e8c0: ldr      x2, [x8]
0207e8c4: bl       #0x281fec4 ; System.Collections.Generic.List<object>$$get_Item
0207e8c8: mov      x26, x0
0207e8cc: cbz      x0, #0x207ec5c
0207e8d0: ldr      x9, [x26, #0x60]
0207e8d4: cbz      x9, #0x207ec48
0207e8d8: mov      w27, wzr
0207e8dc: ldr      w8, [x9, #0x18]
0207e8e0: cmp      w27, w8
0207e8e4: b.ge     #0x207e9cc
0207e8e8: ldr      x2, [x21]
0207e8ec: add      x8, sp, #0xc0
0207e8f0: mov      x0, x9
0207e8f4: mov      w1, w27
0207e8f8: bl       #0x27fbf64 ; System.Collections.Generic.List<FishData>$$get_Item
0207e8fc: ldp      s8, s9, [sp, #0xc0]
0207e900: ldrb     w8, [x23, #0x932]
0207e904: ldr      s10, [sp, #0xc8]
0207e908: cbnz     w8, #0x207e91c
0207e90c: mov      x0, x22
0207e910: bl       #0x18ddbc4
0207e914: mov      w8, #1
0207e918: strb     w8, [x23, #0x932]
0207e91c: ldr      x0, [x22]
0207e920: ldr      w8, [x0, #0xe0]
0207e924: cbnz     w8, #0x207e92c
0207e928: bl       #0x18ddcfc
0207e92c: ldr      s4, [sp, #0x84]
0207e930: fsub     s1, s15, s9
0207e934: fsub     s2, s11, s10
0207e938: ldr      s3, [x26, #0x40]
0207e93c: fsub     s0, s4, s8
0207e940: fmul     s0, s0, s0
0207e944: fmul     s1, s1, s1
0207e948: fadd     s0, s0, s1
0207e94c: fmul     s1, s2, s2
0207e950: fadd     s0, s0, s1
0207e954: fsqrt    s0, s0
0207e958: fcmp     s0, s3
0207e95c: b.pl     #0x207e9bc
0207e960: ldr      s0, [sp, #0x78]
0207e964: ldr      s1, [sp, #0x74]
0207e968: ldur     x8, [x19, #7]
0207e96c: ldr      x9, [sp, #0x108]
0207e970: stp      s11, s0, [sp, #0x90]
0207e974: ldr      s0, [sp, #0x70]
0207e978: stp      s4, s15, [sp, #0x88]
0207e97c: str      x24, [sp, #0xa8]
0207e980: strb     w29, [sp, #0xb0]
0207e984: stp      s1, s0, [sp, #0x98]
0207e988: ldr      s1, [sp, #0x7c]
0207e98c: ldr      s0, [sp, #0x80]
0207e990: stp      s1, s0, [sp, #0xa0]
0207e994: stur     x8, [x28, #7]
0207e998: str      x9, [x28]
0207e99c: add      x1, sp, #0x88
0207e9a0: mov      v0.16b, v8.16b
0207e9a4: mov      v1.16b, v9.16b
0207e9a8: mov      v2.16b, v10.16b
0207e9ac: bl       #0x207de90 ; FishFlock.FishFlockController$$Flee
0207e9b0: fadd     s14, s14, s0
0207e9b4: fadd     s12, s12, s1
0207e9b8: fadd     s13, s13, s2
0207e9bc: ldr      x9, [x26, #0x60]
0207e9c0: add      w27, w27, #1
0207e9c4: cbnz     x9, #0x207e8dc
0207e9c8: b        #0x207ec48
0207e9cc: ldr      x27, [sp, #0x60]
0207e9d0: add      w25, w25, #1
0207e9d4: ldr      x8, [x27, #0x90]
0207e9d8: cbnz     x8, #0x207e888
0207e9dc: b        #0x207ec54
0207e9e0: ldr      s1, [sp, #0x80]
0207e9e4: ldr      s0, [x27, #0x78]
0207e9e8: fneg     s1, s1
0207e9ec: fmul     s0, s0, s1
0207e9f0: bl       #0x3a16bb0 ; expf
0207e9f4: adrp     x8, #0x3ed3000
0207e9f8: ldrb     w8, [x8, #0xb61]
0207e9fc: ldr      x25, [sp, #0x18]
0207ea00: mov      v8.16b, v0.16b
0207ea04: cbnz     w8, #0x207ea1c
0207ea08: mov      x0, x22
0207ea0c: bl       #0x18ddbc4
0207ea10: mov      w8, #1
0207ea14: adrp     x9, #0x3ed3000
0207ea18: strb     w8, [x9, #0xb61]
0207ea1c: ldr      x0, [x22]
0207ea20: ldr      w8, [x0, #0xe0]
0207ea24: cbnz     w8, #0x207ea2c
0207ea28: bl       #0x18ddcfc
0207ea2c: ldp      s1, s0, [sp, #0x58]
0207ea30: ldr      s2, [sp, #0x54]
0207ea34: fadd     s0, s0, s14
0207ea38: fadd     s1, s1, s12
0207ea3c: fadd     s2, s2, s13
0207ea40: fmul     s3, s0, s0
0207ea44: fmul     s4, s1, s1
0207ea48: ldr      s14, [sp, #0x44]
0207ea4c: fadd     s3, s4, s3
0207ea50: fmul     s4, s2, s2
0207ea54: fadd     s3, s4, s3
0207ea58: fsqrt    s3, s3
0207ea5c: fcmp     s3, s14
0207ea60: b.le     #0x207ea78
0207ea64: ldr      s13, [sp, #0x78]
0207ea68: fdiv     s9, s0, s3
0207ea6c: fdiv     s10, s1, s3
0207ea70: fdiv     s12, s2, s3
0207ea74: b        #0x207eac0
0207ea78: adrp     x8, #0x3ed1000
0207ea7c: ldrb     w8, [x8, #0x995]
0207ea80: ldr      s13, [sp, #0x78]
0207ea84: cbnz     w8, #0x207eaa8
0207ea88: adrp     x0, #0x3bf7000
0207ea8c: ldr      x0, [x0, #0x380]
0207ea90: bl       #0x18ddbc4
0207ea94: ldr      s13, [sp, #0x78]
0207ea98: ldr      s14, [sp, #0x44]
0207ea9c: adrp     x8, #0x3ed1000
0207eaa0: mov      w9, #1
0207eaa4: strb     w9, [x8, #0x995]
0207eaa8: adrp     x8, #0x3bf7000
0207eaac: ldr      x8, [x8, #0x380]
0207eab0: ldr      x8, [x8]
0207eab4: ldr      x8, [x8, #0xb8]
0207eab8: ldp      s9, s10, [x8]
0207eabc: ldr      s12, [x8, #8]
0207eac0: adrp     x8, #0x3ed3000
0207eac4: ldrb     w8, [x8, #0xb61]
0207eac8: cbnz     w8, #0x207eae0
0207eacc: mov      x0, x22
0207ead0: bl       #0x18ddbc4
0207ead4: mov      w8, #1
0207ead8: adrp     x9, #0x3ed3000
0207eadc: strb     w8, [x9, #0xb61]
0207eae0: ldr      x0, [x22]
0207eae4: ldr      w8, [x0, #0xe0]
0207eae8: cbnz     w8, #0x207eaf0
0207eaec: bl       #0x18ddcfc
0207eaf0: ldp      s4, s3, [sp, #0x70]
0207eaf4: fmul     s0, s13, s13
0207eaf8: fmul     s1, s3, s3
0207eafc: fadd     s0, s0, s1
0207eb00: fmul     s1, s4, s4
0207eb04: fadd     s0, s1, s0
0207eb08: fsqrt    s0, s0
0207eb0c: fcmp     s0, s14
0207eb10: b.le     #0x207eb24
0207eb14: fdiv     s2, s13, s0
0207eb18: fdiv     s1, s3, s0
0207eb1c: fdiv     s0, s4, s0
0207eb20: b        #0x207eb60
0207eb24: adrp     x8, #0x3ed1000
0207eb28: ldrb     w8, [x8, #0x995]
0207eb2c: cbnz     w8, #0x207eb48
0207eb30: adrp     x0, #0x3bf7000
0207eb34: ldr      x0, [x0, #0x380]
0207eb38: bl       #0x18ddbc4
0207eb3c: adrp     x8, #0x3ed1000
0207eb40: mov      w9, #1
0207eb44: strb     w9, [x8, #0x995]
0207eb48: adrp     x8, #0x3bf7000
0207eb4c: ldr      x8, [x8, #0x380]
0207eb50: ldr      x8, [x8]
0207eb54: ldr      x8, [x8, #0xb8]
0207eb58: ldp      s2, s1, [x8]
0207eb5c: ldr      s0, [x8, #8]
0207eb60: ldr      x8, [sp, #0x48]
0207eb64: ldur     x9, [x19, #7]
0207eb68: ldr      s3, [x27, #0x78]
0207eb6c: ldr      x0, [x8, #0x60]
0207eb70: ldr      x8, [sp, #0x108]
0207eb74: str      x8, [sp, #0xf8]
0207eb78: stur     x9, [sp, #0xff]
0207eb7c: cbz      x0, #0x207ec78
0207eb80: ldr      s6, [sp, #0x7c]
0207eb84: fmov     s4, #1.00000000
0207eb88: fmin     s4, s8, s4
0207eb8c: fsub     s0, s0, s12
0207eb90: adrp     x8, #0x3c2c000
0207eb94: fsub     s1, s1, s10
0207eb98: ldr      x8, [x8, #0x720]
0207eb9c: fmul     s0, s4, s0
0207eba0: fsub     s2, s2, s9
0207eba4: fmul     s3, s6, s3
0207eba8: fmul     s1, s4, s1
0207ebac: fadd     s0, s12, s0
0207ebb0: ldr      s5, [sp, #0x80]
0207ebb4: fmul     s2, s4, s2
0207ebb8: fadd     s1, s10, s1
0207ebbc: fmul     s4, s3, s0
0207ebc0: stp      s1, s0, [sp, #0xd0]
0207ebc4: fadd     s0, s11, s4
0207ebc8: ldr      s4, [sp, #0x84]
0207ebcc: ldr      x3, [x8]
0207ebd0: ldr      x8, [sp, #0xf8]
0207ebd4: ldur     x9, [sp, #0xff]
0207ebd8: fadd     s2, s9, s2
0207ebdc: stp      s6, s5, [sp, #0xd8]
0207ebe0: fmul     s5, s1, s3
0207ebe4: fmul     s3, s2, s3
0207ebe8: fadd     s1, s15, s5
0207ebec: fadd     s3, s4, s3
0207ebf0: str      x24, [sp, #0xe0]
0207ebf4: strb     w29, [sp, #0xe8]
0207ebf8: stp      s3, s1, [sp, #0xc0]
0207ebfc: stp      s0, s2, [sp, #0xc8]
0207ec00: stur     x9, [x25, #7]
0207ec04: str      x8, [x25]
0207ec08: ldr      w1, [sp, #0x6c]
0207ec0c: add      x2, sp, #0xc0
0207ec10: bl       #0x27fbfd4 ; System.Collections.Generic.List<FishData>$$set_Item
0207ec14: ldr      x10, [sp, #0x48]
0207ec18: ldr      w11, [sp, #0x6c]
0207ec1c: ldr      x9, [x10, #0x60]
0207ec20: add      w11, w11, #1
0207ec24: cbnz     x9, #0x207e0fc
0207ec28: b        #0x207ec74
0207ec2c: ldr      x0, [x27, #0x88]
0207ec30: cbz      x0, #0x207ec80
0207ec34: ldr      w8, [x0, #0x18]
0207ec38: add      w20, w20, #1
0207ec3c: cmp      w20, w8
0207ec40: b.lt     #0x207e0b4
0207ec44: b        #0x207ed80
0207ec48: bl       #0x18dde20
0207ec4c: bl       #0x18dde20
0207ec50: bl       #0x18dde20
0207ec54: bl       #0x18dde20
0207ec58: bl       #0x18dde20
0207ec5c: bl       #0x18dde20
0207ec60: bl       #0x18dde20
0207ec64: bl       #0x18dde28
0207ec68: bl       #0x18dde20
0207ec6c: bl       #0x18dde20
0207ec70: bl       #0x18dde20
0207ec74: bl       #0x18dde20
0207ec78: bl       #0x18dde20
0207ec7c: bl       #0x18dde20
0207ec80: bl       #0x18dde20
0207ec84: bl       #0x18dde20
0207ec88: b        #0x207ed08
0207ec8c: b        #0x207ed08
0207ec90: b        #0x207ed08
0207ec94: b        #0x207ed08
0207ec98: b        #0x207ed08
0207ec9c: b        #0x207ed08
0207eca0: b        #0x207ed08
0207eca4: b        #0x207ed08
0207eca8: b        #0x207ed08
0207ecac: b        #0x207ed08
0207ecb0: b        #0x207ed08
0207ecb4: b        #0x207ed08
0207ecb8: b        #0x207ed08
0207ecbc: b        #0x207ed08
0207ecc0: b        #0x207ed08
0207ecc4: b        #0x207ed08
0207ecc8: b        #0x207ed08
0207eccc: b        #0x207ed08
0207ecd0: b        #0x207ed08
0207ecd4: b        #0x207ed08
0207ecd8: b        #0x207ed08
0207ecdc: b        #0x207ed08
0207ece0: b        #0x207ed08
0207ece4: b        #0x207ed08
0207ece8: b        #0x207ed08
0207ecec: b        #0x207ed08
0207ecf0: b        #0x207ed08
0207ecf4: b        #0x207ed08
0207ecf8: b        #0x207ed08
0207ecfc: b        #0x207ed08
0207ed00: b        #0x207ed08
0207ed04: b        #0x207ed08
0207ed08: mov      x19, x0
0207ed0c: cmp      w1, #1
0207ed10: b.ne     #0x207edf4
0207ed14: mov      x0, x19
0207ed18: bl       #0x3a16a60 ; __cxa_begin_catch
0207ed1c: mov      x19, x0
0207ed20: adrp     x0, #0x3bf7000
0207ed24: ldr      x0, [x0, #0xca0]
0207ed28: bl       #0x18ddbd8
0207ed2c: ldr      x8, [x19]
0207ed30: ldr      x1, [x8]
0207ed34: bl       #0x18de22c
0207ed38: tbz      w0, #0, #0x207edc4
0207ed3c: ldr      x19, [x19]
0207ed40: bl       #0x3a16a70 ; __cxa_end_catch
0207ed44: cbz      x19, #0x207ede4
0207ed48: ldr      x8, [x19]
0207ed4c: mov      x0, x19
0207ed50: ldr      x9, [x8, #0x268]
0207ed54: ldr      x1, [x8, #0x270]
0207ed58: blr      x9
0207ed5c: mov      x1, xzr
0207ed60: bl       #0x391122c ; UnityEngine.MonoBehaviour$$print
0207ed64: ldr      x8, [x19]
0207ed68: mov      x0, x19
0207ed6c: ldr      x9, [x8, #0x298]
0207ed70: ldr      x1, [x8, #0x2a0]
0207ed74: blr      x9
0207ed78: mov      x1, xzr
0207ed7c: bl       #0x391122c ; UnityEngine.MonoBehaviour$$print
0207ed80: ldr      x8, [sp, #0x10]
0207ed84: ldr      x8, [x8, #0x28]
0207ed88: ldr      x9, [sp, #0x118]
0207ed8c: cmp      x8, x9
0207ed90: b.ne     #0x207ede8
0207ed94: ldp      x20, x19, [sp, #0x1b0]
0207ed98: ldp      x22, x21, [sp, #0x1a0]
0207ed9c: ldp      x24, x23, [sp, #0x190]
0207eda0: ldp      x26, x25, [sp, #0x180]
0207eda4: ldp      x28, x27, [sp, #0x170]
0207eda8: ldp      x29, x30, [sp, #0x160]
0207edac: ldp      d9, d8, [sp, #0x150]
0207edb0: ldp      d11, d10, [sp, #0x140]
0207edb4: ldp      d13, d12, [sp, #0x130]
0207edb8: ldp      d15, d14, [sp, #0x120]
0207edbc: add      sp, sp, #0x1c0
0207edc0: ret
0207edc4: mov      w0, #8
0207edc8: bl       #0x3a16a80 ; __cxa_allocate_exception
0207edcc: ldr      x8, [x19]
0207edd0: str      x8, [x0]
0207edd4: adrp     x1, #0x3a1c000
0207edd8: add      x1, x1, #0xeb8
0207eddc: mov      x2, xzr
0207ede0: bl       #0x3a16a90 ; __cxa_throw
0207ede4: bl       #0x18dde20
0207ede8: bl       #0x3a16ae0 ; __stack_chk_fail
0207edec: mov      x19, x0
0207edf0: bl       #0x3a16a70 ; __cxa_end_catch
0207edf4: mov      x0, x19
0207edf8: bl       #0x198e98c
0207edfc: bl       #0x15e191c

; 0x207ee4c FishFlock.FishFlockController$$Update | void Update()
0207ee4c: stp      x30, x21, [sp, #-0x20]!
0207ee50: stp      x20, x19, [sp, #0x10]
0207ee54: adrp     x20, #0x3ed5000
0207ee58: ldrb     w8, [x20, #0x4f1]
0207ee5c: mov      x19, x0
0207ee60: tbnz     w8, #0, #0x207ee84
0207ee64: adrp     x0, #0x3c2c000
0207ee68: ldr      x0, [x0, #0x790]
0207ee6c: bl       #0x18ddbc4
0207ee70: adrp     x0, #0x3c2c000
0207ee74: ldr      x0, [x0, #0x798]
0207ee78: bl       #0x18ddbc4
0207ee7c: mov      w8, #1
0207ee80: strb     w8, [x20, #0x4f1]
0207ee84: mov      x0, xzr
0207ee88: bl       #0x39070b8 ; UnityEngine.Time$$get_deltaTime
0207ee8c: ldr      x0, [x19, #0x70]
0207ee90: str      s0, [x19, #0x78]
0207ee94: cbz      x0, #0x207ef50
0207ee98: mov      x1, xzr
0207ee9c: bl       #0x19a22e0 ; SimpleCounter$$Ended
0207eea0: tbz      w0, #0, #0x207eec4
0207eea4: ldrb     w8, [x19, #0x58]
0207eea8: cbz      w8, #0x207eec4
0207eeac: mov      x0, x19
0207eeb0: bl       #0x207d33c ; FishFlock.FishFlockController$$UpdateCollisionData
0207eeb4: ldr      x0, [x19, #0x70]
0207eeb8: cbz      x0, #0x207ef50
0207eebc: mov      x1, xzr
0207eec0: bl       #0x19a22bc ; SimpleCounter$$Reset
0207eec4: ldr      x0, [x19, #0x88]
0207eec8: cbz      x0, #0x207ef50
0207eecc: adrp     x21, #0x3c2c000
0207eed0: ldr      x21, [x21, #0x798]
0207eed4: mov      w20, wzr
0207eed8: ldr      w8, [x0, #0x18]
0207eedc: cmp      w20, w8
0207eee0: b.ge     #0x207ef08
0207eee4: ldr      x2, [x21]
0207eee8: mov      w1, w20
0207eeec: bl       #0x281fec4 ; System.Collections.Generic.List<object>$$get_Item
0207eef0: cbz      x0, #0x207ef50
0207eef4: bl       #0x207aebc ; FishFlock.FishGroup$$UpdateGroupAnchor
0207eef8: ldr      x0, [x19, #0x88]
0207eefc: add      w20, w20, #1
0207ef00: cbnz     x0, #0x207eed8
0207ef04: b        #0x207ef50
0207ef08: ldr      w8, [x19, #0x34]
0207ef0c: cbnz     w8, #0x207ef20
0207ef10: mov      x0, x19
0207ef14: bl       #0x207dfa8 ; FishFlock.FishFlockController$$ComputeFlockBehaviours
0207ef18: ldr      x0, [x19, #0x88]
0207ef1c: cbz      x0, #0x207ef50
0207ef20: mov      w20, wzr
0207ef24: ldr      w8, [x0, #0x18]
0207ef28: cmp      w20, w8
0207ef2c: b.ge     #0x207ef54
0207ef30: ldr      x2, [x21]
0207ef34: mov      w1, w20
0207ef38: bl       #0x281fec4 ; System.Collections.Generic.List<object>$$get_Item
0207ef3c: cbz      x0, #0x207ef50
0207ef40: bl       #0x207b9ac ; FishFlock.FishGroup$$OnUpdate
0207ef44: ldr      x0, [x19, #0x88]
0207ef48: add      w20, w20, #1
0207ef4c: cbnz     x0, #0x207ef24
0207ef50: bl       #0x18dde20
0207ef54: ldp      x20, x19, [sp, #0x10]
0207ef58: ldp      x30, x21, [sp], #0x20
0207ef5c: ret

; 0x207ef60 FishFlock.FishFlockController$$OnDestroy | void OnDestroy()
0207ef60: ldr      x0, [x0, #0x80]
0207ef64: cbz      x0, #0x207ef6c
0207ef68: b        #0x207ef80 ; FishFlock.ThreadManager$$EndTask
0207ef6c: ret

; 0x207ef70 FishFlock.FishFlockController$$ClearAll | void ClearAll()
0207ef70: ldr      x0, [x0, #0x80]
0207ef74: cbz      x0, #0x207ef7c
0207ef78: b        #0x207ef80 ; FishFlock.ThreadManager$$EndTask
0207ef7c: ret

; 0x207f0c4 FishFlock.FishFlockController$$OnDrawGizmos | void OnDrawGizmos()
0207f0c4: stp      x30, x19, [sp, #-0x10]!
0207f0c8: ldrb     w8, [x0, #0x2c]
0207f0cc: cbz      w8, #0x207f130
0207f0d0: ldr      s1, [x0, #0x28]
0207f0d4: ldr      d0, [x0, #0x20]
0207f0d8: adrp     x8, #0x980000
0207f0dc: adrp     x9, #0x980000
0207f0e0: str      s1, [x0, #0xa0]
0207f0e4: ldr      s1, [x8, #0x5d8]
0207f0e8: ldr      s2, [x9, #0x660]
0207f0ec: mov      x19, x0
0207f0f0: str      d0, [x0, #0x98]
0207f0f4: fmov     s0, #1.00000000
0207f0f8: fmov     s3, #1.00000000
0207f0fc: mov      x0, xzr
0207f100: bl       #0x38d8254 ; UnityEngine.Gizmos$$set_color
0207f104: mov      x0, x19
0207f108: mov      x1, xzr
0207f10c: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207f110: cbz      x0, #0x207f138
0207f114: mov      x1, xzr
0207f118: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207f11c: ldp      s3, s4, [x19, #0x98]
0207f120: ldr      s5, [x19, #0xa0]
0207f124: mov      x0, xzr
0207f128: ldp      x30, x19, [sp], #0x10
0207f12c: b        #0x38d7f90 ; UnityEngine.Gizmos$$DrawWireCube
0207f130: ldp      x30, x19, [sp], #0x10
0207f134: ret
0207f138: bl       #0x18dde20

; 0x207ee1c FishFlock.FishFlockController$$GetSeparationVector | Vector3 GetSeparationVector(Vector3 diff, float len, float neighbourDistance)
0207ee1c: fdiv     s4, s3, s4
0207ee20: fmov     s5, #1.00000000
0207ee24: fsub     s4, s5, s4
0207ee28: fmin     s5, s4, s5
0207ee2c: fcmp     s4, #0.0
0207ee30: fmov     s4, wzr
0207ee34: fcsel    s4, s5, s4, pl
0207ee38: fdiv     s3, s4, s3
0207ee3c: fmul     s0, s0, s3
0207ee40: fmul     s1, s1, s3
0207ee44: fmul     s2, s2, s3
0207ee48: ret

; 0x207ee00 FishFlock.FishFlockController$$VecMag | float VecMag(Vector3 v)
0207ee00: fmul     s0, s0, s0
0207ee04: fmul     s1, s1, s1
0207ee08: fadd     s0, s0, s1
0207ee0c: fmul     s1, s2, s2
0207ee10: fadd     s0, s1, s0
0207ee14: fsqrt    s0, s0
0207ee18: ret

; 0x207f13c FishFlock.FishFlockController$$.ctor | void .ctor()
0207f13c: stp      x30, x23, [sp, #-0x30]!
0207f140: stp      x22, x21, [sp, #0x10]
0207f144: stp      x20, x19, [sp, #0x20]
0207f148: adrp     x23, #0x3ed5000
0207f14c: adrp     x20, #0x3c2c000
0207f150: adrp     x22, #0x3c29000
0207f154: adrp     x21, #0x3c2c000
0207f158: ldrb     w8, [x23, #0x4f2]
0207f15c: ldr      x20, [x20, #0x7e8]
0207f160: ldr      x22, [x22, #0xf50]
0207f164: ldr      x21, [x21, #0x7f0]
0207f168: mov      x19, x0
0207f16c: tbnz     w8, #0, #0x207f19c
0207f170: adrp     x0, #0x3c2c000
0207f174: ldr      x0, [x0, #0x7f0]
0207f178: bl       #0x18ddbc4
0207f17c: adrp     x0, #0x3c29000
0207f180: ldr      x0, [x0, #0xf50]
0207f184: bl       #0x18ddbc4
0207f188: adrp     x0, #0x3c2c000
0207f18c: ldr      x0, [x0, #0x7e8]
0207f190: bl       #0x18ddbc4
0207f194: mov      w8, #1
0207f198: strb     w8, [x23, #0x4f2]
0207f19c: adrp     x8, #0x97f000
0207f1a0: ldr      d0, [x8, #0xf08]
0207f1a4: mov      w9, #0x41c80000
0207f1a8: str      w9, [x19, #0x28]
0207f1ac: adrp     x9, #0x980000
0207f1b0: str      d0, [x19, #0x20]
0207f1b4: ldr      d0, [x9, #0x418]
0207f1b8: mov      x9, #0x40800000
0207f1bc: movk     x9, #3, lsl #32
0207f1c0: mov      w8, #1
0207f1c4: str      x9, [x19, #0x40]
0207f1c8: mov      w9, #0x41a00000
0207f1cc: strb     w8, [x19, #0x2c]
0207f1d0: str      w9, [x19, #0x48]
0207f1d4: str      d0, [x19, #0x38]
0207f1d8: strb     w8, [x19, #0x58]
0207f1dc: ldr      x0, [x20]
0207f1e0: bl       #0x18dde10
0207f1e4: mov      x1, xzr
0207f1e8: mov      x20, x0
0207f1ec: bl       #0x19a2304 ; SimpleCounter$$.ctor
0207f1f0: mov      x0, x19
0207f1f4: str      x20, [x0, #0x70]!
0207f1f8: mov      x1, x20
0207f1fc: bl       #0x18ddb68
0207f200: ldr      x0, [x22]
0207f204: bl       #0x18dde10
0207f208: ldr      x1, [x21]
0207f20c: mov      x20, x0
0207f210: bl       #0x281f960 ; System.Collections.Generic.List<object>$$.ctor
0207f214: mov      x0, x19
0207f218: str      x20, [x0, #0x88]!
0207f21c: mov      x1, x20
0207f220: bl       #0x18ddb68
0207f224: mov      x0, x19
0207f228: ldp      x20, x19, [sp, #0x20]
0207f22c: ldp      x22, x21, [sp, #0x10]
0207f230: mov      x1, xzr
0207f234: ldp      x30, x23, [sp], #0x30
0207f238: b        #0x39112c0 ; UnityEngine.MonoBehaviour$$.ctor

; 0x207f23c FishFlock.FlockPredator$$get_Position | Vector3 get_Position()
0207f23c: ldp      s0, s1, [x0, #0x28]
0207f240: ldr      s2, [x0, #0x30]
0207f244: ret

; 0x207f248 FishFlock.FlockPredator$$Update | void Update()
0207f248: stp      x30, x19, [sp, #-0x10]!
0207f24c: mov      x1, xzr
0207f250: mov      x19, x0
0207f254: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207f258: cbz      x0, #0x207f274
0207f25c: mov      x1, xzr
0207f260: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207f264: stp      s0, s1, [x19, #0x28]
0207f268: str      s2, [x19, #0x30]
0207f26c: ldp      x30, x19, [sp], #0x10
0207f270: ret
0207f274: bl       #0x18dde20

; 0x207f278 FishFlock.FlockPredator$$OnDrawGizmos | void OnDrawGizmos()
0207f278: stp      x30, x19, [sp, #-0x10]!
0207f27c: adrp     x8, #0x980000
0207f280: ldr      s3, [x8, #0x8b0]
0207f284: mov      x19, x0
0207f288: fmov     s0, wzr
0207f28c: fmov     s1, wzr
0207f290: fmov     s2, #1.00000000
0207f294: mov      x0, xzr
0207f298: bl       #0x38d8254 ; UnityEngine.Gizmos$$set_color
0207f29c: mov      x0, x19
0207f2a0: mov      x1, xzr
0207f2a4: bl       #0x390da7c ; UnityEngine.Component$$get_transform
0207f2a8: cbz      x0, #0x207f2c4
0207f2ac: mov      x1, xzr
0207f2b0: bl       #0x391b010 ; UnityEngine.Transform$$get_position
0207f2b4: ldr      s3, [x19, #0x20]
0207f2b8: mov      x0, xzr
0207f2bc: ldp      x30, x19, [sp], #0x10
0207f2c0: b        #0x38d7e50 ; UnityEngine.Gizmos$$DrawWireSphere
0207f2c4: bl       #0x18dde20

; 0x207f2c8 FishFlock.FlockPredator$$.ctor | void .ctor()
0207f2c8: stp      x30, x21, [sp, #-0x20]!
0207f2cc: stp      x20, x19, [sp, #0x10]
0207f2d0: mov      w8, #0x41200000
0207f2d4: mov      w20, #1
0207f2d8: str      w8, [x0, #0x20]
0207f2dc: strb     w20, [x0, #0x24]
0207f2e0: adrp     x21, #0x3ed1000
0207f2e4: ldrb     w8, [x21, #0x995]
0207f2e8: mov      x19, x0
0207f2ec: cbnz     w8, #0x207f300
0207f2f0: adrp     x0, #0x3bf7000
0207f2f4: ldr      x0, [x0, #0x380]
0207f2f8: bl       #0x18ddbc4
0207f2fc: strb     w20, [x21, #0x995]
0207f300: adrp     x8, #0x3bf7000
0207f304: ldr      x8, [x8, #0x380]
0207f308: mov      x0, x19
0207f30c: mov      x1, xzr
0207f310: ldr      x8, [x8]
0207f314: ldr      x8, [x8, #0xb8]
0207f318: ldr      d0, [x8]
0207f31c: ldr      s1, [x8, #8]
0207f320: str      d0, [x19, #0x28]
0207f324: str      s1, [x19, #0x30]
0207f328: ldp      x20, x19, [sp, #0x10]
0207f32c: ldp      x30, x21, [sp], #0x20
0207f330: b        #0x39112c0 ; UnityEngine.MonoBehaviour$$.ctor

; 0x207f334 FishFlock.ThreadManager$$SetupSingleton | static void SetupSingleton()
0207f334: stp      x30, x21, [sp, #-0x20]!
0207f338: stp      x20, x19, [sp, #0x10]
0207f33c: adrp     x21, #0x3ed5000
0207f340: adrp     x20, #0x3c2c000
0207f344: adrp     x19, #0x3bf7000
0207f348: ldrb     w8, [x21, #0x4f3]
0207f34c: ldr      x20, [x20, #0x7d0]
0207f350: ldr      x19, [x19, #0x468]
0207f354: tbnz     w8, #0, #0x207f39c
0207f358: adrp     x0, #0x3c2c000
0207f35c: ldr      x0, [x0, #0x7f8]
0207f360: bl       #0x18ddbc4
0207f364: adrp     x0, #0x3bf8000
0207f368: ldr      x0, [x0, #0xcc0]
0207f36c: bl       #0x18ddbc4
0207f370: adrp     x0, #0x3bf7000
0207f374: ldr      x0, [x0, #0x468]
0207f378: bl       #0x18ddbc4
0207f37c: adrp     x0, #0x3c2c000
0207f380: ldr      x0, [x0, #0x7d0]
0207f384: bl       #0x18ddbc4
0207f388: adrp     x0, #0x3c2c000
0207f38c: ldr      x0, [x0, #0x800]
0207f390: bl       #0x18ddbc4
0207f394: mov      w8, #1
0207f398: strb     w8, [x21, #0x4f3]
0207f39c: ldr      x8, [x20]
0207f3a0: ldr      x0, [x19]
0207f3a4: ldr      x8, [x8, #0xb8]
0207f3a8: ldr      w9, [x0, #0xe0]
0207f3ac: ldr      x19, [x8, #8]
0207f3b0: cbnz     w9, #0x207f3b8
0207f3b4: bl       #0x18ddcfc
0207f3b8: mov      x0, x19
0207f3bc: mov      x1, xzr
0207f3c0: mov      x2, xzr
0207f3c4: bl       #0x390f060 ; UnityEngine.Object$$op_Inequality
0207f3c8: tbz      w0, #0, #0x207f3d8
0207f3cc: ldp      x20, x19, [sp, #0x10]
0207f3d0: ldp      x30, x21, [sp], #0x20
0207f3d4: ret
0207f3d8: adrp     x8, #0x3bf8000
0207f3dc: ldr      x8, [x8, #0xcc0]
0207f3e0: adrp     x19, #0x3c2c000
0207f3e4: ldr      x0, [x8]
0207f3e8: ldr      x19, [x19, #0x800]
0207f3ec: bl       #0x18dde10
0207f3f0: ldr      x1, [x19]
0207f3f4: mov      x2, xzr
0207f3f8: mov      x19, x0
0207f3fc: bl       #0x390f9f8 ; UnityEngine.GameObject$$.ctor
0207f400: ldr      x8, [x20]
0207f404: mov      x1, x19
0207f408: ldr      x8, [x8, #0xb8]
0207f40c: str      x19, [x8]
0207f410: ldr      x8, [x20]
0207f414: ldr      x0, [x8, #0xb8]
0207f418: bl       #0x18ddb68
0207f41c: ldr      x8, [x20]
0207f420: ldr      x8, [x8, #0xb8]
0207f424: ldr      x0, [x8]
0207f428: cbz      x0, #0x207f4c0
0207f42c: mov      w1, #0x3d
0207f430: mov      x2, xzr
0207f434: bl       #0x39144a4 ; UnityEngine.Object$$set_hideFlags
0207f438: ldr      x8, [x20]
0207f43c: ldr      x8, [x8, #0xb8]
0207f440: ldr      x0, [x8]
0207f444: cbz      x0, #0x207f4c0
0207f448: adrp     x8, #0x3c2c000
0207f44c: ldr      x8, [x8, #0x7f8]
0207f450: ldr      x1, [x8]
0207f454: bl       #0x22b9ee4 ; UnityEngine.GameObject$$AddComponent<object>
0207f458: ldr      x8, [x20]
0207f45c: mov      x1, x0
0207f460: ldr      x8, [x8, #0xb8]
0207f464: str      x0, [x8, #8]!
0207f468: mov      x0, x8
0207f46c: bl       #0x18ddb68
0207f470: mov      x0, xzr
0207f474: bl       #0x30cbc90 ; System.Environment$$get_ProcessorCount
0207f478: mov      w19, w0
0207f47c: mov      x0, xzr
0207f480: bl       #0x30cbc90 ; System.Environment$$get_ProcessorCount
0207f484: mov      w1, w0
0207f488: mov      w0, w19
0207f48c: mov      x2, xzr
0207f490: bl       #0x30fd760 ; System.Threading.ThreadPool$$SetMinThreads
0207f494: mov      x0, xzr
0207f498: bl       #0x30cbc90 ; System.Environment$$get_ProcessorCount
0207f49c: mov      w19, w0
0207f4a0: mov      x0, xzr
0207f4a4: bl       #0x30cbc90 ; System.Environment$$get_ProcessorCount
0207f4a8: mov      w1, w0
0207f4ac: mov      w0, w19
0207f4b0: ldp      x20, x19, [sp, #0x10]
0207f4b4: mov      x2, xzr
0207f4b8: ldp      x30, x21, [sp], #0x20
0207f4bc: b        #0x30fd750 ; System.Threading.ThreadPool$$SetMaxThreads
0207f4c0: bl       #0x18dde20

; 0x207f4c4 FishFlock.ThreadManager$$Start | void Start()
0207f4c4: stp      x30, x23, [sp, #-0x30]!
0207f4c8: stp      x22, x21, [sp, #0x10]
0207f4cc: stp      x20, x19, [sp, #0x20]
0207f4d0: adrp     x22, #0x3ed5000
0207f4d4: adrp     x23, #0x3c0d000
0207f4d8: adrp     x20, #0x3c2c000
0207f4dc: adrp     x21, #0x3c13000
0207f4e0: ldrb     w8, [x22, #0x4f4]
0207f4e4: ldr      x23, [x23, #0xa90]
0207f4e8: ldr      x20, [x20, #0x808]
0207f4ec: ldr      x21, [x21, #0x230]
0207f4f0: mov      x19, x0
0207f4f4: tbnz     w8, #0, #0x207f524
0207f4f8: adrp     x0, #0x3c13000
0207f4fc: ldr      x0, [x0, #0x230]
0207f500: bl       #0x18ddbc4
0207f504: adrp     x0, #0x3c2c000
0207f508: ldr      x0, [x0, #0x808]
0207f50c: bl       #0x18ddbc4
0207f510: adrp     x0, #0x3c0d000
0207f514: ldr      x0, [x0, #0xa90]
0207f518: bl       #0x18ddbc4
0207f51c: mov      w8, #1
0207f520: strb     w8, [x22, #0x4f4]
0207f524: ldr      x0, [x23]
0207f528: bl       #0x18dde10
0207f52c: ldr      x2, [x20]
0207f530: mov      x1, x19
0207f534: mov      x3, xzr
0207f538: mov      x20, x0
0207f53c: bl       #0x2c76be4 ; UnityEngine.Events.UnityAction<Scene>$$.ctor
0207f540: ldr      x0, [x21]
0207f544: ldr      w8, [x0, #0xe0]
0207f548: cbnz     w8, #0x207f550
0207f54c: bl       #0x18ddcfc
0207f550: mov      x0, x20
0207f554: ldp      x20, x19, [sp, #0x20]
0207f558: ldp      x22, x21, [sp, #0x10]
0207f55c: mov      x1, xzr
0207f560: ldp      x30, x23, [sp], #0x30
0207f564: b        #0x3924d08 ; UnityEngine.SceneManagement.SceneManager$$add_sceneUnloaded

; 0x207f568 FishFlock.ThreadManager$$Update | void Update()
0207f568: str      x30, [sp, #-0x30]!
0207f56c: stp      x22, x21, [sp, #0x10]
0207f570: stp      x20, x19, [sp, #0x20]
0207f574: adrp     x19, #0x3ed5000
0207f578: ldrb     w8, [x19, #0x4f5]
0207f57c: mov      x20, x0
0207f580: tbnz     w8, #0, #0x207f5a4
0207f584: adrp     x0, #0x3c2c000
0207f588: ldr      x0, [x0, #0x810]
0207f58c: bl       #0x18ddbc4
0207f590: adrp     x0, #0x3c2c000
0207f594: ldr      x0, [x0, #0x818]
0207f598: bl       #0x18ddbc4
0207f59c: mov      w8, #1
0207f5a0: strb     w8, [x19, #0x4f5]
0207f5a4: ldr      x19, [x20, #0x20]
0207f5a8: strb     wzr, [sp, #0xc]
0207f5ac: add      x1, sp, #0xc
0207f5b0: mov      x0, x19
0207f5b4: mov      x2, xzr
0207f5b8: bl       #0x30f21e8 ; System.Threading.Monitor$$Enter
0207f5bc: ldr      x0, [x20, #0x20]
0207f5c0: cbz      x0, #0x207f608
0207f5c4: adrp     x22, #0x3c2c000
0207f5c8: ldr      x22, [x22, #0x818]
0207f5cc: mov      w21, wzr
0207f5d0: ldr      w8, [x0, #0x18]
0207f5d4: cmp      w21, w8
0207f5d8: b.ge     #0x207f60c
0207f5dc: ldr      x2, [x22]
0207f5e0: mov      w1, w21
0207f5e4: bl       #0x281fec4 ; System.Collections.Generic.List<object>$$get_Item
0207f5e8: cbz      x0, #0x207f638
0207f5ec: ldr      x0, [x0, #0x20]
0207f5f0: cbz      x0, #0x207f5fc
0207f5f4: mov      x1, xzr
0207f5f8: bl       #0x30f3e98 ; System.Threading.EventWaitHandle$$Set
0207f5fc: ldr      x0, [x20, #0x20]
0207f600: add      w21, w21, #1
0207f604: cbnz     x0, #0x207f5d0
0207f608: bl       #0x18dde20
0207f60c: mov      x21, xzr
0207f610: ldrb     w8, [sp, #0xc]
0207f614: cbz      w8, #0x207f624
0207f618: mov      x0, x19
0207f61c: mov      x1, xzr
0207f620: bl       #0x30f6428 ; System.Threading.Monitor$$Exit
0207f624: cbnz     x21, #0x207f63c
0207f628: ldp      x20, x19, [sp, #0x20]
0207f62c: ldp      x22, x21, [sp, #0x10]
0207f630: ldr      x30, [sp], #0x30
0207f634: ret
0207f638: bl       #0x18dde20
0207f63c: mov      x0, x21
0207f640: bl       #0x18dde18
0207f644: b        #0x207f654
0207f648: b        #0x207f654
0207f64c: b        #0x207f654
0207f650: b        #0x207f654
0207f654: mov      x20, x0
0207f658: cmp      w1, #1
0207f65c: b.ne     #0x207f674
0207f660: mov      x0, x20
0207f664: bl       #0x3a16a60 ; __cxa_begin_catch
0207f668: ldr      x21, [x0]
0207f66c: bl       #0x3a16a70 ; __cxa_end_catch
0207f670: b        #0x207f610
0207f674: mov      x21, xzr
0207f678: b        #0x207f680
0207f67c: mov      x20, x0
0207f680: ldrb     w8, [sp, #0xc]
0207f684: cbz      w8, #0x207f694
0207f688: mov      x0, x19
0207f68c: mov      x1, xzr
0207f690: bl       #0x30f6428 ; System.Threading.Monitor$$Exit
0207f694: cbnz     x21, #0x207f6a0
0207f698: mov      x0, x20
0207f69c: bl       #0x198e98c
0207f6a0: mov      x0, x21
0207f6a4: bl       #0x18dde18
0207f6a8: bl       #0x15e191c

; 0x207f6ac FishFlock.ThreadManager$$OnDestroy | void OnDestroy()
0207f6ac: b        #0x207f6b0 ; FishFlock.ThreadManager$$Reset

; 0x207f8ec FishFlock.ThreadManager$$OnApplicationQuit | void OnApplicationQuit()
0207f8ec: b        #0x207f6b0 ; FishFlock.ThreadManager$$Reset

; 0x207f8f0 FishFlock.ThreadManager$$OnSceneIsUnloaded | void OnSceneIsUnloaded(Scene arg0)
0207f8f0: b        #0x207f6b0 ; FishFlock.ThreadManager$$Reset

; 0x207f6b0 FishFlock.ThreadManager$$Reset | void Reset()
0207f6b0: sub      sp, sp, #0x80
0207f6b4: str      x30, [sp, #0x40]
0207f6b8: stp      x24, x23, [sp, #0x50]
0207f6bc: stp      x22, x21, [sp, #0x60]
0207f6c0: stp      x20, x19, [sp, #0x70]
0207f6c4: adrp     x19, #0x3ed5000
0207f6c8: ldrb     w8, [x19, #0x4f6]
0207f6cc: mov      x20, x0
0207f6d0: tbnz     w8, #0, #0x207f718
0207f6d4: adrp     x0, #0x3c2c000
0207f6d8: ldr      x0, [x0, #0x820]
0207f6dc: bl       #0x18ddbc4
0207f6e0: adrp     x0, #0x3c2c000
0207f6e4: ldr      x0, [x0, #0x828]
0207f6e8: bl       #0x18ddbc4
0207f6ec: adrp     x0, #0x3c2c000
0207f6f0: ldr      x0, [x0, #0x830]
0207f6f4: bl       #0x18ddbc4
0207f6f8: adrp     x0, #0x3c2c000
0207f6fc: ldr      x0, [x0, #0x838]
0207f700: bl       #0x18ddbc4
0207f704: adrp     x0, #0x3c2c000
0207f708: ldr      x0, [x0, #0x840]
0207f70c: bl       #0x18ddbc4
0207f710: mov      w8, #1
0207f714: strb     w8, [x19, #0x4f6]
0207f718: stp      xzr, xzr, [sp, #0x20]
0207f71c: str      xzr, [sp, #0x30]
0207f720: ldr      x19, [x20, #0x20]
0207f724: strb     wzr, [sp, #0x4c]
0207f728: add      x1, sp, #0x4c
0207f72c: mov      x0, x19
0207f730: mov      x2, xzr
0207f734: bl       #0x30f21e8 ; System.Threading.Monitor$$Enter
0207f738: ldr      x0, [x20, #0x20]
0207f73c: cbz      x0, #0x207f81c
0207f740: adrp     x8, #0x3c2c000
0207f744: ldr      x8, [x8, #0x840]
0207f748: ldr      x1, [x8]
0207f74c: add      x8, sp, #8
0207f750: bl       #0x2820dcc ; System.Collections.Generic.List<object>$$GetEnumerator
0207f754: ldur     q0, [sp, #8]
0207f758: ldr      x8, [sp, #0x18]
0207f75c: adrp     x21, #0x3c2c000
0207f760: adrp     x24, #0x3c2c000
0207f764: ldr      x21, [x21, #0x828]
0207f768: ldr      x24, [x24, #0x820]
0207f76c: str      q0, [sp, #0x20]
0207f770: str      x8, [sp, #0x30]
0207f774: ldr      x1, [x21]
0207f778: add      x0, sp, #0x20
0207f77c: bl       #0x25f69e4 ; System.Collections.Generic.List.Enumerator<object>$$MoveNext
0207f780: tbz      w0, #0, #0x207f794
0207f784: ldr      x8, [sp, #0x30]
0207f788: cbz      x8, #0x207f810
0207f78c: strb     wzr, [x8, #0x10]
0207f790: b        #0x207f774
0207f794: mov      x21, xzr
0207f798: ldr      x1, [x24]
0207f79c: add      x0, sp, #0x20
0207f7a0: bl       #0x25f69e0 ; System.Collections.Generic.List.Enumerator<object>$$Dispose
0207f7a4: cbnz     x21, #0x207f820
0207f7a8: ldr      x8, [x20, #0x20]
0207f7ac: cbz      x8, #0x207f828
0207f7b0: ldp      w2, w9, [x8, #0x18]
0207f7b4: add      w9, w9, #1
0207f7b8: cmp      w2, #1
0207f7bc: stp      wzr, w9, [x8, #0x18]
0207f7c0: b.lt     #0x207f7dc
0207f7c4: ldr      x0, [x8, #0x10]
0207f7c8: mov      w1, wzr
0207f7cc: mov      x3, xzr
0207f7d0: bl       #0x30a4d18 ; System.Array$$Clear
0207f7d4: mov      x20, xzr
0207f7d8: b        #0x207f7e0
0207f7dc: mov      x20, xzr
0207f7e0: ldrb     w8, [sp, #0x4c]
0207f7e4: cbz      w8, #0x207f7f4
0207f7e8: mov      x0, x19
0207f7ec: mov      x1, xzr
0207f7f0: bl       #0x30f6428 ; System.Threading.Monitor$$Exit
0207f7f4: cbnz     x20, #0x207f814
0207f7f8: ldp      x20, x19, [sp, #0x70]
0207f7fc: ldp      x22, x21, [sp, #0x60]
0207f800: ldp      x24, x23, [sp, #0x50]
0207f804: ldr      x30, [sp, #0x40]
0207f808: add      sp, sp, #0x80
0207f80c: ret
0207f810: bl       #0x18dde20
0207f814: mov      x0, x20
0207f818: bl       #0x18dde18
0207f81c: bl       #0x18dde20
0207f820: mov      x0, x21
0207f824: bl       #0x18dde18
0207f828: bl       #0x18dde20
0207f82c: b        #0x207f83c
0207f830: b        #0x207f83c
0207f834: b        #0x207f83c
0207f838: b        #0x207f83c
0207f83c: mov      x22, x1
0207f840: mov      x23, x0
0207f844: b        #0x207f884
0207f848: b        #0x207f84c
0207f84c: mov      x22, x1
0207f850: mov      x23, x0
0207f854: cmp      w22, #1
0207f858: b.ne     #0x207f870
0207f85c: mov      x0, x23
0207f860: bl       #0x3a16a60 ; __cxa_begin_catch
0207f864: ldr      x21, [x0]
0207f868: bl       #0x3a16a70 ; __cxa_end_catch
0207f86c: b        #0x207f798
0207f870: mov      x21, xzr
0207f874: ldr      x1, [x24]
0207f878: add      x0, sp, #0x20
0207f87c: bl       #0x25f69e0 ; System.Collections.Generic.List.Enumerator<object>$$Dispose
0207f880: cbnz     x21, #0x207f8a8
0207f884: cmp      w22, #1
0207f888: b.ne     #0x207f8a0
0207f88c: mov      x0, x23
0207f890: bl       #0x3a16a60 ; __cxa_begin_catch
0207f894: ldr      x20, [x0]
0207f898: bl       #0x3a16a70 ; __cxa_end_catch
0207f89c: b        #0x207f7e0
0207f8a0: mov      x20, xzr
0207f8a4: b        #0x207f8c0
0207f8a8: mov      x0, x21
0207f8ac: bl       #0x18dde18
0207f8b0: mov      x22, x1
0207f8b4: mov      x23, x0
0207f8b8: b        #0x207f874
0207f8bc: mov      x23, x0
0207f8c0: ldrb     w8, [sp, #0x4c]
0207f8c4: cbz      w8, #0x207f8d4
0207f8c8: mov      x0, x19
0207f8cc: mov      x1, xzr
0207f8d0: bl       #0x30f6428 ; System.Threading.Monitor$$Exit
0207f8d4: cbnz     x20, #0x207f8e0
0207f8d8: mov      x0, x23
0207f8dc: bl       #0x198e98c
0207f8e0: mov      x0, x20
0207f8e4: bl       #0x18dde18
0207f8e8: bl       #0x15e191c

; 0x207dcd4 FishFlock.ThreadManager$$DoTask | static ThreadProcess DoTask(Action callback)
0207dcd4: str      x30, [sp, #-0x30]!
0207dcd8: stp      x22, x21, [sp, #0x10]
0207dcdc: stp      x20, x19, [sp, #0x20]
0207dce0: adrp     x22, #0x3ed5000
0207dce4: adrp     x20, #0x3c2c000
0207dce8: adrp     x21, #0x3c2c000
0207dcec: ldrb     w8, [x22, #0x4f7]
0207dcf0: ldr      x20, [x20, #0x7c8]
0207dcf4: ldr      x21, [x21, #0x7d0]
0207dcf8: mov      x19, x0
0207dcfc: tbnz     w8, #0, #0x207dd2c
0207dd00: adrp     x0, #0x3c2c000
0207dd04: ldr      x0, [x0, #0x7d8]
0207dd08: bl       #0x18ddbc4
0207dd0c: adrp     x0, #0x3c2c000
0207dd10: ldr      x0, [x0, #0x7d0]
0207dd14: bl       #0x18ddbc4
0207dd18: adrp     x0, #0x3c2c000
0207dd1c: ldr      x0, [x0, #0x7c8]
0207dd20: bl       #0x18ddbc4
0207dd24: mov      w8, #1
0207dd28: strb     w8, [x22, #0x4f7]
0207dd2c: bl       #0x207f334 ; FishFlock.ThreadManager$$SetupSingleton
0207dd30: ldr      x0, [x20]
0207dd34: bl       #0x18dde10
0207dd38: mov      x1, x19
0207dd3c: mov      x20, x0
0207dd40: bl       #0x207f8fc ; FishFlock.ThreadProcess$$.ctor
0207dd44: ldr      x8, [x21]
0207dd48: ldr      x8, [x8, #0xb8]
0207dd4c: ldr      x8, [x8, #8]
0207dd50: cbz      x8, #0x207de18
0207dd54: ldr      x19, [x8, #0x20]
0207dd58: strb     wzr, [sp, #0xc]
0207dd5c: add      x1, sp, #0xc
0207dd60: mov      x0, x19
0207dd64: mov      x2, xzr
0207dd68: bl       #0x30f21e8 ; System.Threading.Monitor$$Enter
0207dd6c: ldr      x8, [x21]
0207dd70: ldr      x8, [x8, #0xb8]
0207dd74: ldr      x8, [x8, #8]
0207dd78: cbz      x8, #0x207de24
0207dd7c: ldr      x0, [x8, #0x20]
0207dd80: cbz      x0, #0x207de28
0207dd84: adrp     x9, #0x3c2c000
0207dd88: ldr      x9, [x9, #0x7d8]
0207dd8c: ldr      w10, [x0, #0x1c]
0207dd90: ldr      x8, [x0, #0x10]
0207dd94: ldr      x9, [x9]
0207dd98: add      w10, w10, #1
0207dd9c: str      w10, [x0, #0x1c]
0207dda0: cbz      x8, #0x207de2c
0207dda4: ldrsw    x10, [x0, #0x18]
0207dda8: ldr      w11, [x8, #0x18]
0207ddac: cmp      w10, w11
0207ddb0: b.hs     #0x207ddd4
0207ddb4: add      w9, w10, #1
0207ddb8: add      x8, x8, x10, lsl #3
0207ddbc: str      w9, [x0, #0x18]
0207ddc0: str      x20, [x8, #0x20]!
0207ddc4: mov      x0, x8
0207ddc8: mov      x1, x20
0207ddcc: bl       #0x18ddb68
0207ddd0: b        #0x207dde8
0207ddd4: ldr      x8, [x9, #0x20]
0207ddd8: ldr      x8, [x8, #0xc0]
0207dddc: ldr      x2, [x8, #0x70]
0207dde0: mov      x1, x20
0207dde4: bl       #0x2820194 ; System.Collections.Generic.List<object>$$AddWithResize
0207dde8: mov      x21, xzr
0207ddec: ldrb     w8, [sp, #0xc]
0207ddf0: cbz      w8, #0x207de00
0207ddf4: mov      x0, x19
0207ddf8: mov      x1, xzr
0207ddfc: bl       #0x30f6428 ; System.Threading.Monitor$$Exit
0207de00: cbnz     x21, #0x207de1c
0207de04: mov      x0, x20
0207de08: ldp      x20, x19, [sp, #0x20]
0207de0c: ldp      x22, x21, [sp, #0x10]
0207de10: ldr      x30, [sp], #0x30
0207de14: ret
0207de18: bl       #0x18dde20
0207de1c: mov      x0, x21
0207de20: bl       #0x18dde18
0207de24: bl       #0x18dde20
0207de28: bl       #0x18dde20
0207de2c: bl       #0x18dde20
0207de30: b        #0x207de38
0207de34: b        #0x207de38
0207de38: mov      x22, x0
0207de3c: cmp      w1, #1
0207de40: b.ne     #0x207de58
0207de44: mov      x0, x22
0207de48: bl       #0x3a16a60 ; __cxa_begin_catch
0207de4c: ldr      x21, [x0]
0207de50: bl       #0x3a16a70 ; __cxa_end_catch
0207de54: b        #0x207ddec
0207de58: mov      x21, xzr
0207de5c: b        #0x207de64
0207de60: mov      x22, x0
0207de64: ldrb     w8, [sp, #0xc]
0207de68: cbz      w8, #0x207de78
0207de6c: mov      x0, x19
0207de70: mov      x1, xzr
0207de74: bl       #0x30f6428 ; System.Threading.Monitor$$Exit
0207de78: cbnz     x21, #0x207de84
0207de7c: mov      x0, x22
0207de80: bl       #0x198e98c
0207de84: mov      x0, x21
0207de88: bl       #0x18dde18
0207de8c: bl       #0x15e191c

; 0x207ef80 FishFlock.ThreadManager$$EndTask | static void EndTask(ThreadProcess process)
0207ef80: sub      sp, sp, #0x30
0207ef84: stp      x30, x21, [sp, #0x10]
0207ef88: stp      x20, x19, [sp, #0x20]
0207ef8c: adrp     x19, #0x3ed5000
0207ef90: ldrb     w8, [x19, #0x4f8]
0207ef94: mov      x20, x0
0207ef98: tbnz     w8, #0, #0x207efbc
0207ef9c: adrp     x0, #0x3c2c000
0207efa0: ldr      x0, [x0, #0x7e0]
0207efa4: bl       #0x18ddbc4
0207efa8: adrp     x0, #0x3c2c000
0207efac: ldr      x0, [x0, #0x7d0]
0207efb0: bl       #0x18ddbc4
0207efb4: mov      w8, #1
0207efb8: strb     w8, [x19, #0x4f8]
0207efbc: cbz      x20, #0x207f04c
0207efc0: adrp     x21, #0x3c2c000
0207efc4: ldr      x21, [x21, #0x7d0]
0207efc8: strb     wzr, [x20, #0x10]
0207efcc: ldr      x8, [x21]
0207efd0: ldr      x8, [x8, #0xb8]
0207efd4: ldr      x8, [x8, #8]
0207efd8: cbz      x8, #0x207f04c
0207efdc: ldr      x19, [x8, #0x20]
0207efe0: strb     wzr, [sp, #0xc]
0207efe4: add      x1, sp, #0xc
0207efe8: mov      x0, x19
0207efec: mov      x2, xzr
0207eff0: bl       #0x30f21e8 ; System.Threading.Monitor$$Enter
0207eff4: ldr      x8, [x21]
0207eff8: ldr      x8, [x8, #0xb8]
0207effc: ldr      x8, [x8, #8]
0207f000: cbz      x8, #0x207f058
0207f004: ldr      x0, [x8, #0x20]
0207f008: cbz      x0, #0x207f05c
0207f00c: adrp     x8, #0x3c2c000
0207f010: ldr      x8, [x8, #0x7e0]
0207f014: ldr      x2, [x8]
0207f018: mov      x1, x20
0207f01c: bl       #0x2821a24 ; System.Collections.Generic.List<object>$$Remove
0207f020: mov      x20, xzr
0207f024: ldrb     w8, [sp, #0xc]
0207f028: cbz      w8, #0x207f038
0207f02c: mov      x0, x19
0207f030: mov      x1, xzr
0207f034: bl       #0x30f6428 ; System.Threading.Monitor$$Exit
0207f038: cbnz     x20, #0x207f050
0207f03c: ldp      x20, x19, [sp, #0x20]
0207f040: ldp      x30, x21, [sp, #0x10]
0207f044: add      sp, sp, #0x30
0207f048: ret
0207f04c: bl       #0x18dde20
0207f050: mov      x0, x20
0207f054: bl       #0x18dde18
0207f058: bl       #0x18dde20
0207f05c: bl       #0x18dde20
0207f060: b        #0x207f06c
0207f064: b        #0x207f06c
0207f068: b        #0x207f06c
0207f06c: mov      x21, x0
0207f070: cmp      w1, #1
0207f074: b.ne     #0x207f08c
0207f078: mov      x0, x21
0207f07c: bl       #0x3a16a60 ; __cxa_begin_catch
0207f080: ldr      x20, [x0]
0207f084: bl       #0x3a16a70 ; __cxa_end_catch
0207f088: b        #0x207f024
0207f08c: mov      x20, xzr
0207f090: b        #0x207f098
0207f094: mov      x21, x0
0207f098: ldrb     w8, [sp, #0xc]
0207f09c: cbz      w8, #0x207f0ac
0207f0a0: mov      x0, x19
0207f0a4: mov      x1, xzr
0207f0a8: bl       #0x30f6428 ; System.Threading.Monitor$$Exit
0207f0ac: cbnz     x20, #0x207f0b8
0207f0b0: mov      x0, x21
0207f0b4: bl       #0x198e98c
0207f0b8: mov      x0, x20
0207f0bc: bl       #0x18dde18
0207f0c0: bl       #0x15e191c

; 0x207f9ec FishFlock.ThreadManager$$.ctor | void .ctor()
0207f9ec: str      x30, [sp, #-0x30]!
0207f9f0: stp      x22, x21, [sp, #0x10]
0207f9f4: stp      x20, x19, [sp, #0x20]
0207f9f8: adrp     x21, #0x3ed5000
0207f9fc: adrp     x22, #0x3c2c000
0207fa00: adrp     x20, #0x3c2c000
0207fa04: ldrb     w8, [x21, #0x4f9]
0207fa08: ldr      x22, [x22, #0x858]
0207fa0c: ldr      x20, [x20, #0x860]
0207fa10: mov      x19, x0
0207fa14: tbnz     w8, #0, #0x207fa38
0207fa18: adrp     x0, #0x3c2c000
0207fa1c: ldr      x0, [x0, #0x860]
0207fa20: bl       #0x18ddbc4
0207fa24: adrp     x0, #0x3c2c000
0207fa28: ldr      x0, [x0, #0x858]
0207fa2c: bl       #0x18ddbc4
0207fa30: mov      w8, #1
0207fa34: strb     w8, [x21, #0x4f9]
0207fa38: ldr      x0, [x22]
0207fa3c: bl       #0x18dde10
0207fa40: ldr      x1, [x20]
0207fa44: mov      x20, x0
0207fa48: bl       #0x281f960 ; System.Collections.Generic.List<object>$$.ctor
0207fa4c: mov      x0, x19
0207fa50: str      x20, [x0, #0x20]!
0207fa54: mov      x1, x20
0207fa58: bl       #0x18ddb68
0207fa5c: mov      x0, x19
0207fa60: ldp      x20, x19, [sp, #0x20]
0207fa64: ldp      x22, x21, [sp, #0x10]
0207fa68: mov      x1, xzr
0207fa6c: ldr      x30, [sp], #0x30
0207fa70: b        #0x39112c0 ; UnityEngine.MonoBehaviour$$.ctor

; 0x207fa74 FishFlock.ThreadProcess$$get_AutoEvt | AutoResetEvent get_AutoEvt()
0207fa74: ldr      x0, [x0, #0x20]
0207fa78: ret

; 0x207fa7c FishFlock.ThreadProcess$$set_AutoEvt | void set_AutoEvt(AutoResetEvent value)
0207fa7c: str      x1, [x0, #0x20]!
0207fa80: b        #0x18ddb68

; 0x207f8fc FishFlock.ThreadProcess$$.ctor | void .ctor(Action _callback)
0207f8fc: str      x30, [sp, #-0x40]!
0207f900: stp      x24, x23, [sp, #0x10]
0207f904: stp      x22, x21, [sp, #0x20]
0207f908: stp      x20, x19, [sp, #0x30]
0207f90c: adrp     x24, #0x3ed5000
0207f910: adrp     x23, #0x3c2c000
0207f914: adrp     x22, #0x3c23000
0207f918: adrp     x21, #0x3c2c000
0207f91c: ldrb     w8, [x24, #0x4fa]
0207f920: ldr      x23, [x23, #0x848]
0207f924: ldr      x22, [x22, #0x618]
0207f928: ldr      x21, [x21, #0x850]
0207f92c: mov      x20, x1
0207f930: mov      x19, x0
0207f934: tbnz     w8, #0, #0x207f964
0207f938: adrp     x0, #0x3c2c000
0207f93c: ldr      x0, [x0, #0x848]
0207f940: bl       #0x18ddbc4
0207f944: adrp     x0, #0x3c2c000
0207f948: ldr      x0, [x0, #0x850]
0207f94c: bl       #0x18ddbc4
0207f950: adrp     x0, #0x3c23000
0207f954: ldr      x0, [x0, #0x618]
0207f958: bl       #0x18ddbc4
0207f95c: mov      w8, #1
0207f960: strb     w8, [x24, #0x4fa]
0207f964: mov      w24, #1
0207f968: mov      x0, x19
0207f96c: mov      x1, xzr
0207f970: strb     w24, [x19, #0x10]
0207f974: bl       #0x30c6a24 ; System.Object$$.ctor
0207f978: mov      x0, x19
0207f97c: str      x20, [x0, #0x18]!
0207f980: mov      x1, x20
0207f984: bl       #0x18ddb68
0207f988: strb     w24, [x19, #0x10]
0207f98c: ldr      x0, [x23]
0207f990: bl       #0x18dde10
0207f994: mov      w1, #1
0207f998: mov      x2, xzr
0207f99c: mov      x20, x0
0207f9a0: bl       #0x30e93b4 ; System.Threading.AutoResetEvent$$.ctor
0207f9a4: mov      x0, x19
0207f9a8: str      x20, [x0, #0x20]!
0207f9ac: mov      x1, x20
0207f9b0: bl       #0x18ddb68
0207f9b4: ldr      x0, [x22]
0207f9b8: bl       #0x18dde10
0207f9bc: ldr      x2, [x21]
0207f9c0: mov      x1, x19
0207f9c4: mov      x3, xzr
0207f9c8: mov      x20, x0
0207f9cc: bl       #0x30f6e38 ; System.Threading.WaitCallback$$.ctor
0207f9d0: mov      x0, x20
0207f9d4: ldp      x20, x19, [sp, #0x30]
0207f9d8: ldp      x22, x21, [sp, #0x20]
0207f9dc: ldp      x24, x23, [sp, #0x10]
0207f9e0: mov      x1, xzr
0207f9e4: ldr      x30, [sp], #0x40
0207f9e8: b        #0x30fdfe0 ; System.Threading.ThreadPool$$QueueUserWorkItem

; 0x207fa84 FishFlock.ThreadProcess$$DoRun | void DoRun()
0207fa84: stp      x30, x19, [sp, #-0x10]!
0207fa88: ldrb     w8, [x0, #0x10]
0207fa8c: cbz      w8, #0x207facc
0207fa90: mov      x19, x0
0207fa94: ldr      x8, [x19, #0x18]
0207fa98: cbz      x8, #0x207fad4
0207fa9c: ldr      x9, [x8, #0x18]
0207faa0: ldr      x0, [x8, #0x40]
0207faa4: ldr      x1, [x8, #0x28]
0207faa8: blr      x9
0207faac: ldr      x0, [x19, #0x20]
0207fab0: cbz      x0, #0x207fad4
0207fab4: ldr      x8, [x0]
0207fab8: mov      w1, #0x64
0207fabc: ldp      x9, x2, [x8, #0x1f8]
0207fac0: blr      x9
0207fac4: ldrb     w8, [x19, #0x10]
0207fac8: cbnz     w8, #0x207fa94
0207facc: ldp      x30, x19, [sp], #0x10
0207fad0: ret
0207fad4: bl       #0x18dde20

; 0x207f8f4 FishFlock.ThreadProcess$$Stop | void Stop()
0207f8f4: strb     wzr, [x0, #0x10]
0207f8f8: ret

; 0x207fad8 FishFlock.ThreadProcess$$<.ctor>b__6_0 | void <.ctor>b__6_0(object p)
0207fad8: b        #0x207fa84 ; FishFlock.ThreadProcess$$DoRun

; 0x207fadc FishFlock.VecHelpers$$mul | static Vector3 mul(Vector3 l, Vector3 r)
0207fadc: fmul     s0, s0, s3
0207fae0: fmul     s1, s1, s4
0207fae4: fmul     s2, s2, s5
0207fae8: ret

; 0x207faec FishFlock.VecHelpers$$mul | static Vector3 mul(Vector3 l, float r)
0207faec: fmul     s0, s0, s3
0207faf0: fmul     s1, s1, s3
0207faf4: fmul     s2, s2, s3
0207faf8: ret

; 0x207fafc FishFlock.VecHelpers$$.ctor | void .ctor()
0207fafc: mov      x1, xzr
0207fb00: b        #0x30c6a24 ; System.Object$$.ctor

; 0x207fb04 FishFlock.Utils.MinMaxAttribute$$.ctor | void .ctor(float min, float max)
0207fb04: stp      d9, d8, [sp, #-0x20]!
0207fb08: stp      x30, x19, [sp, #0x10]
0207fb0c: mov      x1, xzr
0207fb10: mov      v8.16b, v1.16b
0207fb14: mov      v9.16b, v0.16b
0207fb18: mov      x19, x0
0207fb1c: bl       #0x390ab40 ; UnityEngine.PropertyAttribute$$.ctor
0207fb20: stp      s9, s8, [x19, #0x10]
0207fb24: ldp      x30, x19, [sp, #0x10]
0207fb28: ldp      d9, d8, [sp], #0x20
0207fb2c: ret

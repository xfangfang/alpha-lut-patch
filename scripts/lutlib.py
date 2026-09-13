"""机内 LUT 的 python 复刻（用于生成菜单图标预览）。"""
import numpy as np

KNOTS = 1024
MATRIX_SCALE = 1024

def load_ltc(path):
    """读 .LTC（v2 缓存）：4B VERSION + 8B srcLen + 8B srcMtime + 1024×4B + 9×4B，全大端。"""
    with open(path, "rb") as f:
        ver = int.from_bytes(f.read(4), "big", signed=True)
        src_len = int.from_bytes(f.read(8), "big", signed=True)
        src_mtime = int.from_bytes(f.read(8), "big", signed=True)
        gamma = np.frombuffer(f.read(KNOTS * 4), dtype=">i4").astype(np.float64)
        matrix = np.frombuffer(f.read(9 * 4), dtype=">i4").astype(np.float64)
    return {
        "version": ver, "src_len": src_len, "src_mtime": src_mtime,
        "gamma": gamma, "matrix": matrix.reshape(3, 3),
    }

class Lut:
    def __init__(self, gamma, matrix):
        self.gamma = np.clip(gamma, 0, 1023) / 1023.0
        self.matrix = matrix / float(MATRIX_SCALE)
        self._x = np.linspace(0.0, 1.0, KNOTS)

    @classmethod
    def from_ltc(cls, path):
        d = load_ltc(path)
        return cls(d["gamma"], d["matrix"])

    @classmethod
    def identity(cls):
        return cls(np.arange(KNOTS, dtype=np.float64),
                   np.array([[MATRIX_SCALE, 0, 0], [0, MATRIX_SCALE, 0],
                             [0, 0, MATRIX_SCALE]], dtype=np.float64))

    def curve(self, x):
        """把 [0,1] 的数组过一遍伽马曲线。"""
        return np.interp(x, self._x, self.gamma)

    def apply(self, rgb, matrix_first=True):
        """rgb: (...,3) ∈ [0,1] → 输出同形状。"""
        rgb = np.asarray(rgb, dtype=np.float64)
        if matrix_first:
            z = rgb @ self.matrix.T
            return np.clip(np.interp(z, self._x, self.gamma), 0.0, 1.0)
        u = np.interp(rgb, self._x, self.gamma)
        return np.clip(u @ self.matrix.T, 0.0, 1.0)

    def apply_u8(self, arr, matrix_first=True):
        """uint8 (...,3) → uint8 (...,3)。"""
        return np.round(self.apply(arr.astype(np.float64) / 255.0, matrix_first) * 255.0).astype(np.uint8)

def load_cube(cube_path):
    """读 .cube → numpy (N,N,N,3)，索引方式 a[b, g, r]（红变化最快，与 Java Cube 一致）。"""
    size, data = None, []
    with open(cube_path, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.upper().startswith("LUT_3D_SIZE"):
                size = int(line.split()[-1])
                continue
            if line[0].isalpha():
                continue
            parts = line.split()
            if len(parts) == 3:
                try:
                    data.append([float(p) for p in parts])
                except ValueError:
                    pass
    n = size ** 3
    if len(data) != n:
        raise ValueError(f"bad cube {cube_path}: size={size} rows={len(data)}")

    return np.array(data, dtype=np.float64).reshape(size, size, size, 3)

def apply_cube(cube_path, rgb):
    """trilinear 套用 .cube。rgb: (...,3) ∈ [0,1]。"""
    lut = load_cube(cube_path)
    size = lut.shape[0]
    co = np.clip(rgb, 0, 1) * (size - 1)
    i0 = np.floor(co).astype(int)
    i1 = np.minimum(i0 + 1, size - 1)
    i0 = np.minimum(i0, size - 2)
    f = co - i0
    i1 = np.minimum(i0 + 1, size - 1)
    ir0, ig0, ib0 = i0[..., 0], i0[..., 1], i0[..., 2]
    ir1, ig1, ib1 = i1[..., 0], i1[..., 1], i1[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]

    def at(r, g, b):
        return lut[b, g, r]

    c00 = at(ir0, ig0, ib0) * (1 - fr) + at(ir1, ig0, ib0) * fr
    c01 = at(ir0, ig0, ib1) * (1 - fr) + at(ir1, ig0, ib1) * fr
    c10 = at(ir0, ig1, ib0) * (1 - fr) + at(ir1, ig1, ib0) * fr
    c11 = at(ir0, ig1, ib1) * (1 - fr) + at(ir1, ig1, ib1) * fr
    c0 = c00 * (1 - fg) + c10 * fg
    c1 = c01 * (1 - fg) + c11 * fg
    return np.clip(c0 * (1 - fb) + c1 * fb, 0.0, 1.0)

def write_cube(path, lut, header=()):
    """按 .cube 标准写盘（红变化最快、`%.6f`），确定性输出（同样输入 → 同样字节）。"""
    size = lut.shape[0]
    lines = list(header)
    lines.append('LUT_3D_SIZE %d' % size)
    lines += ['DOMAIN_MIN 0.0 0.0 0.0', 'DOMAIN_MAX 1.0 1.0 1.0', '']
    for b in range(size):
        for g in range(size):
            for r in range(size):
                v = lut[b, g, r]
                lines.append('%.6f %.6f %.6f' % (v[0], v[1], v[2]))

    with open(path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        d = load_ltc(p)
        M = d["matrix"] / MATRIX_SCALE
        g = d["gamma"] / 1023.0
        print(p.split("/")[-1])
        print("   gamma[0,256,512,768,1023] =",
              [round(float(g[i]), 3) for i in (0, 256, 512, 768, 1023)])
        for r in M:
            print("   M", " ".join(f"{v:+.3f}" for v in r))

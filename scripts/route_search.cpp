#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <queue>
#include <vector>
struct Q {
  float f, g;
  uint32_t n;
  bool operator<(Q const &o) const { return f > o.f; }
};
int main(int argc, char **argv) {
  std::ifstream in(argv[1], std::ios::binary);
  uint32_t W, H, L;
  in.read((char *)&W, 4);
  in.read((char *)&H, 4);
  in.read((char *)&L, 4);
  uint32_t S = W * H, N = S * L;
  std::vector<uint8_t> b(N), p(N, 255);
  in.read((char *)b.data(), N);
  std::vector<float> d(N, INFINITY);
  int xmin = W, ymin = H, xmax = 0, ymax = 0;
  for (uint32_t n = 0; n < N; n++)
    if (b[n] & 8) {
      int x = n % W, y = (n % S) / W;
      xmin = std::min(xmin, x);
      xmax = std::max(xmax, x);
      ymin = std::min(ymin, y);
      ymax = std::max(ymax, y);
    }
  auto heur = [&](uint32_t n) {
    int x = n % W, y = (n % S) / W, dx = std::max({xmin - x, 0, x - xmax}),
        dy = std::max({ymin - y, 0, y - ymax});
    return float(std::max(dx, dy) + .41421356 * std::min(dx, dy));
  };
  std::priority_queue<Q> q;
  for (uint32_t n = 0; n < N; n++)
    if ((b[n] & 5) == 4) {
      d[n] = 0;
      p[n] = 254;
      q.push({heur(n), 0, n});
    }
  int dx[] = {-1, 1, 0, 0, -1, 1, -1, 1}, dy[] = {0, 0, -1, 1, -1, -1, 1, 1};
  uint32_t goal = N, count = 0;
  while (!q.empty()) {
    auto a = q.top();
    q.pop();
    if (a.g > d[a.n] + .001)
      continue;
    if (b[a.n] & 8) {
      goal = a.n;
      break;
    }
    if (++count > 14000000)
      break;
    int x = a.n % W, y = (a.n % S) / W, z = a.n / S;
    for (int k = 0; k < 8; k++) {
      int xx = x + dx[k], yy = y + dy[k];
      if (xx < 0 || xx >= W || yy < 0 || yy >= H)
        continue;
      uint32_t nn = z * S + yy * W + xx;
      if (b[nn] & 1)
        continue;
      if (dx[k] && dy[k] &&
          ((b[z * S + y * W + xx] & 1) || (b[z * S + yy * W + x] & 1)))
        continue;
      float ng = a.g + (k < 4 ? 1 : 1.41421356);
      if (ng + .001 < d[nn]) {
        d[nn] = ng;
        p[nn] = k;
        q.push({ng + heur(nn), ng, nn});
      }
    }
    if (!(b[a.n] & 2))
      for (int zz = 0; zz < L; zz++) {
        if (zz == z)
          continue;
        uint32_t nn = zz * S + y * W + x;
        if (b[nn] & 3)
          continue;
        float ng = a.g + 50;
        if (ng + .001 < d[nn]) {
          d[nn] = ng;
          p[nn] = 8 + z;
          q.push({ng + heur(nn), ng, nn});
        }
      }
  }
  std::ofstream out(argv[2], std::ios::binary);
  if (goal == N)
    return 2;
  std::vector<uint32_t> path;
  for (uint32_t n = goal;;) {
    path.push_back(n);
    int k = p[n];
    if (k == 254)
      break;
    if (k < 8)
      n -= dy[k] * W + dx[k];
    else
      n = (k - 8) * S + n % S;
  }
  std::reverse(path.begin(), path.end());
  out.write((char *)path.data(), path.size() * 4);
}

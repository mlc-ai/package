#include <z3++.h>

int main() {
  z3::context cxx_ctx;
  z3::expr x = cxx_ctx.bool_const("x");
  z3::solver cxx_solver(cxx_ctx);
  cxx_solver.add(x);
  if (cxx_solver.check() != z3::sat) {
    return 1;
  }

  Z3_config cfg = Z3_mk_config();
  Z3_context ctx = Z3_mk_context(cfg);
  Z3_solver solver = Z3_mk_solver(ctx);
  Z3_solver_inc_ref(ctx, solver);
  Z3_solver_dec_ref(ctx, solver);
  Z3_del_context(ctx);
  Z3_del_config(cfg);
  return 0;
}

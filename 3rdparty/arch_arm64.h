#ifndef MPIP_ARCH_ARM64_H
#define MPIP_ARCH_ARM64_H

#define ARCH_CPU_NAME "arm64"
#define ARCH_CACHE_LINE_SIZE 64
#define ARCH_TIMER_NAME "rdtsc unavailable"
#define ARCH_CYCLES_PER_SECOND 0

static inline void  mpiP_atomic_wmb(void) {}
static inline int   mpiP_atomic_isync(void) { return 0; }

static inline void* mpiP_atomic_swap(void** ptr, void* val) {
  void* old = *ptr;
  *ptr = val;
  return old;
}

static inline int mpiP_atomic_cas(void** ptr, void** expected, void* desired) {
  if (*ptr == *expected) {
    *ptr = desired;
    return 1;
  }
  return 0;
}

#endif  // MPIP_ARCH_ARM64_H

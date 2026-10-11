package io.archguard.engine;

import java.util.*;

/** Iterative Kosaraju: O(V+E), no recursion-depth failure on large package graphs. */
public final class Cycles {
  private Cycles() {}

  public static List<List<String>> components(Map<String, Set<String>> input) {
    Map<String, Set<String>> graph = new TreeMap<>(), reverse = new TreeMap<>();
    input.forEach(
        (v, edges) -> {
          graph.computeIfAbsent(v, k -> new TreeSet<>()).addAll(edges);
          for (String e : edges) graph.computeIfAbsent(e, k -> new TreeSet<>());
        });
    graph.forEach(
        (v, edges) -> {
          reverse.computeIfAbsent(v, k -> new TreeSet<>());
          for (String e : edges) reverse.computeIfAbsent(e, k -> new TreeSet<>()).add(v);
        });
    Set<String> seen = new HashSet<>();
    List<String> order = new ArrayList<>();
    record Frame(String vertex, Iterator<String> edges) {}
    for (String start : graph.keySet()) {
      if (!seen.add(start)) continue;
      Deque<Frame> stack = new ArrayDeque<>();
      stack.push(new Frame(start, graph.get(start).iterator()));
      while (!stack.isEmpty()) {
        Frame f = stack.peek();
        if (f.edges().hasNext()) {
          String n = f.edges().next();
          if (seen.add(n)) stack.push(new Frame(n, graph.get(n).iterator()));
        } else {
          order.add(f.vertex());
          stack.pop();
        }
      }
    }
    seen.clear();
    Collections.reverse(order);
    List<List<String>> result = new ArrayList<>();
    for (String start : order) {
      if (!seen.add(start)) continue;
      List<String> component = new ArrayList<>();
      Deque<String> stack = new ArrayDeque<>();
      stack.push(start);
      while (!stack.isEmpty()) {
        String v = stack.pop();
        component.add(v);
        for (String e : reverse.get(v)) if (seen.add(e)) stack.push(e);
      }
      Collections.sort(component);
      if (component.size() > 1) result.add(List.copyOf(component));
    }
    result.sort(Comparator.comparing(c -> c.get(0)));
    return List.copyOf(result);
  }
}

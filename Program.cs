using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace GrammarParser
{
    public class Production
    {
        public string LeftHandSide { get; set; }
        public List<string> RightHandSide { get; set; }

        public Production(string lhs, List<string> rhs)
        {
            LeftHandSide = lhs;
            RightHandSide = rhs;
        }

        public override string ToString()
        {
            return $"{LeftHandSide} -> {string.Join("|", RightHandSide)}";
        }
    }

    public class Grammar
    {
        public List<Production> Productions { get; set; } = new();
        public List<string> NonTerminals { get; set; } = new() { "E", "E'", "T", "T'", "F" };
        public List<string> Terminals { get; set; } = new() { "id", "+", "*", "(", ")", "$" };
        public string StartSymbol { get; set; } = "E";

        public void LoadFromFile(string path)
        {
            if (!File.Exists(path))
            {
                throw new FileNotFoundException("Grammar file not found.");
            }

            var lines = File.ReadAllLines(path);

            foreach (var line in lines)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;

                var parts = line.Split("->");
                if (parts.Length != 2)
                {
                    Console.WriteLine($"Invalid grammar line: {line}");
                    continue;
                }

                var lhs = parts[0].Trim();
                var rhsSymbols = parts[1].Trim().Split('|', StringSplitOptions.RemoveEmptyEntries);
                Productions.Add(new Production(lhs, new List<string>(rhsSymbols)));
            }
        }

        public void PrintGrammar()
        {
            Console.WriteLine("Grammar Productions:");
            foreach (var prod in Productions)
            {
                Console.WriteLine(prod);
            }
        }
    }
    public class State
    {
        public string Name { get; set; }
        public bool IsStart { get; set; }
        public bool IsAccept { get; set; }

        public State(string name, bool isStart = false, bool isAccept = false)
        {
            Name = name;
            IsStart = isStart;
            IsAccept = isAccept;
        }
    }

    
    public class TransitionRule
    {
        public State CurrentState { get; set; }
        public string InputSymbol { get; set; }
        public string StackTop { get; set; }
        public State NextState { get; set; }
        public List<string> StackAction { get; set; } 

        public TransitionRule(State currentState, string inputSymbol, string stackTop, State nextState, List<string> stackAction)
        {
            CurrentState = currentState;
            InputSymbol = inputSymbol;
            StackTop = stackTop;
            NextState = nextState;
            StackAction = stackAction;
        }
    }

    public class DPDA
    {
        private List<State> states = new();
        private List<TransitionRule> transitions = new();
        private Stack<string> stack = new();

        public void AddState(State state)
        {
            states.Add(state);
        }

        public void AddTransition(TransitionRule rule)
        {
            transitions.Add(rule);
        }

        public bool Process(string input)
        {

            var startState = states.FirstOrDefault(s => s.IsStart);
            if (startState == null) throw new InvalidOperationException("Start state not defined.");

            var acceptState = states.FirstOrDefault(s => s.IsAccept);
            if (acceptState == null) throw new InvalidOperationException("Accept state not defined.");

            State currentState = startState;
            stack.Clear();
            stack.Push("$"); // علامت پایه پشته

            Queue<string> inputQueue = new(input.Split(' ', StringSplitOptions.RemoveEmptyEntries));

            while (true)
            {
                string currentInput = inputQueue.Count > 0 ? inputQueue.Peek() : "ε";
                string stackTop = stack.Count > 0 ? stack.Peek() : "ε";

                TransitionRule rule = transitions.FirstOrDefault(t =>
                    t.CurrentState.Name == currentState.Name &&
                    (t.InputSymbol == currentInput || t.InputSymbol == "ε") &&
                    t.StackTop == stackTop
                );

                if (rule == null)
                    break; 

                if (rule.InputSymbol != "ε" && inputQueue.Count > 0)
                    inputQueue.Dequeue();

                if (stack.Count > 0)
                    stack.Pop();

                for (int i = rule.StackAction.Count - 1; i >= 0; i--)
                {
                    if (rule.StackAction[i] != "ε")
                        stack.Push(rule.StackAction[i]);
                }

                currentState = rule.NextState;
            }
            Console.WriteLine(inputQueue.Count.ToString() + " " + stack.Peek() + " " + currentState.IsAccept+ " "+currentState.Name);
            return inputQueue.Count == 0 && stack.Peek() == "$" && currentState.IsAccept;
        }
    }
    public class LL1Parser
    {
        private readonly Grammar grammar;
        private readonly Dictionary<string, HashSet<string>> First = new();
        private readonly Dictionary<string, HashSet<string>> Follow = new();
        public readonly Dictionary<(string NonTerminal, string Terminal), Production> Table = new();

        public LL1Parser(Grammar g)
        {
            grammar = g;
            InitializeSets();
            ComputeFirst();
            ComputeFollow();
            BuildParsingTable();
        }

        private void InitializeSets()
        {
            foreach (var nt in grammar.NonTerminals)
            {
                First[nt] = new HashSet<string>();
                Follow[nt] = new HashSet<string>();
            }
            Follow[grammar.StartSymbol].Add("$"); // End of input symbol
        }

        private void ComputeFirst()
        {
            bool changed;
            do
            {
                changed = false;

                foreach (var prod in grammar.Productions)
                {
                    var lhs = prod.LeftHandSide;
                    var rhs = prod.RightHandSide;

                    var before = First[lhs].Count;
                    var firstSet = FirstOf(rhs);
                    First[lhs].UnionWith(firstSet);
                    if (First[lhs].Count != before) changed = true;
                }

            } while (changed);
        }

        private void ComputeFollow()
        {
            bool changed;
            do
            {
                changed = false;

                foreach (var prod in grammar.Productions)
                {
                    var lhs = prod.LeftHandSide;
                    var rhs = prod.RightHandSide;

                    for (int i = 0; i < rhs.Count; i++)
                    {
                        var B = rhs[i];
                        if (!grammar.NonTerminals.Contains(B)) continue;

                        var beta = rhs.Skip(i + 1).ToList();
                        var firstBeta = FirstOf(beta);

                        int before = Follow[B].Count;
                        Follow[B].UnionWith(firstBeta.Where(x => x != "ε"));

                        if (firstBeta.Contains("ε") || beta.Count == 0)
                            Follow[B].UnionWith(Follow[lhs]);

                        if (Follow[B].Count != before)
                            changed = true;
                    }
                }

            } while (changed);
        }

        private HashSet<string> FirstOf(List<string> symbols)
        {
            var result = new HashSet<string>();

            if (symbols.Count == 0)
            {
                result.Add("ε");
                return result;
            }

            foreach (var sym in symbols)
            {
                if (grammar.Terminals.Contains(sym))
                {
                    result.Add(sym);
                    break;
                }
                else if (grammar.NonTerminals.Contains(sym))
                {
                    result.UnionWith(First[sym].Where(x => x != "ε"));

                    if (!First[sym].Contains("ε"))
                        break;
                }
                else if (sym == "ε")
                {
                    result.Add("ε");
                    break;
                }

                if (sym == symbols.Last())
                    result.Add("ε");
            }

            return result;
        }

        private void BuildParsingTable()
        {
            foreach (var prod in grammar.Productions)
            {
                var lhs = prod.LeftHandSide;
                var rhs = prod.RightHandSide;
                var firstSet = FirstOf(rhs);

                foreach (var terminal in firstSet)
                {
                    if (terminal != "ε")
                        Table[(lhs, terminal)] = prod;
                }

                if (firstSet.Contains("ε"))
                {
                    foreach (var follow in Follow[lhs])
                        Table[(lhs, follow)] = prod;
                }
            }
        }

        public void PrintTable()
        {
            var terminals = grammar.Terminals.ToList();
            terminals.Add("$");

            Console.WriteLine("\nLL(1) Parsing Table:");
            Console.Write("{0,-12}", "Non-Term");
            foreach (var t in terminals)
                Console.Write("{0,-20}", t);
            Console.WriteLine();

            foreach (var nt in grammar.NonTerminals)
            {
                Console.Write("{0,-12}", nt);
                foreach (var t in terminals)
                {
                    if (Table.TryGetValue((nt, t), out var prod))
                        Console.Write("{0,-20}", prod.ToString());
                    else
                        Console.Write("{0,-20}", "");
                }
                Console.WriteLine();
            }
        }
    }
    
    class Program
    {
        static void Main(string[] args)
        {
            Grammar grammar = new Grammar();

            try
            {
                grammar.LoadFromFile("grammar.txt");
                grammar.PrintGrammar();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
            }
            //Console.WriteLine(grammar.Productions[1].RightHandSide[0]);
            var parser = new LL1Parser(grammar);
            parser.PrintTable();
            //var q0 = new State("q0", isStart: true);
            //var q1 = new State("q1");
            //var qAccept = new State("q_accept", isAccept: true);

            //DPDA dpda = new();
            //dpda.AddState(q0);
            //dpda.AddState(q1);
            //dpda.AddState(qAccept);

            //dpda.AddTransition(new TransitionRule(q0, "a", "$", q0, new List<string> {"a","$"}));
            //dpda.AddTransition(new TransitionRule(q0, "a", "a", q0, new List<string> { "a","a" }));
            //dpda.AddTransition(new TransitionRule(q0, "b", "a", q1, new List<string> { "ε" }));
            //dpda.AddTransition(new TransitionRule(q1, "b", "a", q1, new List<string> { "ε" }));
            //dpda.AddTransition(new TransitionRule(q1, "ε", "$", qAccept, new List<string> { "$" }));
            //Console.Write("Enter input string (space-separated): ");
            //string input = Console.ReadLine();

            //bool accepted = dpda.Process(input);

            //Console.WriteLine(accepted ? "Accepted" : "Rejected");


        }
    }
}

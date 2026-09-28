import re
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, deque
import json

class Production:
    def __init__(self, left: str, right: List[str]):
        self.left = left  
        self.right = right  
    
    def __str__(self):
        return f"{self.left} -> {' '.join(self.right)}"
    
    def __repr__(self):
        return self.__str__()

class Grammar:
    
    def __init__(self):
        self.productions: List[Production] = []
        self.terminals: Set[str] = set()
        self.non_terminals: Set[str] = set()
        self.start_symbol: str = ""
        self.first_sets: Dict[str, Set[str]] = {}
        self.follow_sets: Dict[str, Set[str]] = {}
        self.parse_table: Dict[Tuple[str, str], Production] = {}
    
    def add_production(self, left: str, right: List[str]):
        production = Production(left, right)
        self.productions.append(production)
        self.non_terminals.add(left)
        
        # تشخیص terminal ها
        for symbol in right:
            if symbol != 'ε' and not symbol.isupper():
                self.terminals.add(symbol)
    
    def set_start_symbol(self, symbol: str):
        self.start_symbol = symbol
    
    @classmethod
    def from_file(cls, filename: str):
        grammar = cls()
        
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '->' in line:
                left, right = line.split('->', 1)
                left = left.strip()
                right_symbols = right.strip().split()
                
                if not right_symbols:
                    right_symbols = ['ε']
                
                grammar.add_production(left, right_symbols)
                
                if not grammar.start_symbol:
                    grammar.set_start_symbol(left)
        
        grammar._compute_first_sets()
        grammar._compute_follow_sets()
        grammar._build_parse_table()
        
        return grammar
    
    def _compute_first_sets(self):
        for terminal in self.terminals:
            self.first_sets[terminal] = {terminal}
        
        for non_terminal in self.non_terminals:
            self.first_sets[non_terminal] = set()
        
        self.first_sets['ε'] = {'ε'}
        
        changed = True
        while changed:
            changed = False
            for production in self.productions:
                first_before = len(self.first_sets[production.left])
                
                for symbol in production.right:
                    if symbol == 'ε':
                        self.first_sets[production.left].add('ε')
                        break
                    
                    symbol_first = self.first_sets.get(symbol, set())
                    self.first_sets[production.left] |= (symbol_first - {'ε'})
                    
                    if 'ε' not in symbol_first:
                        break
                else:
                    self.first_sets[production.left].add('ε')
                
                if len(self.first_sets[production.left]) > first_before:
                    changed = True
    
    def _compute_follow_sets(self):
        for non_terminal in self.non_terminals:
            self.follow_sets[non_terminal] = set()
        
        self.follow_sets[self.start_symbol].add('$')
        
        changed = True
        while changed:
            changed = False
            
            for production in self.productions:
                for i, symbol in enumerate(production.right):
                    if symbol in self.non_terminals:
                        follow_before = len(self.follow_sets[symbol])
                        
                        beta = production.right[i+1:]
                        
                        if beta:  
                            first_beta = self._first_of_string(beta)
                            self.follow_sets[symbol] |= (first_beta - {'ε'})
                            
                            if 'ε' in first_beta:
                                self.follow_sets[symbol] |= self.follow_sets[production.left]
                                
                            self.follow_sets[symbol] |= self.follow_sets[production.left]
                        
                        if len(self.follow_sets[symbol]) > follow_before:
                            changed = True
    
    def _first_of_string(self, symbols: List[str]) -> Set[str]:
        if not symbols:
            return {'ε'}
        
        result = set()
        
        for symbol in symbols:
            symbol_first = self.first_sets.get(symbol, set())
            result |= (symbol_first - {'ε'})
            
            if 'ε' not in symbol_first:
                break
        else:
            result.add('ε')
        
        return result
    
    def _build_parse_table(self):
        self.parse_table = {}
        
        for production in self.productions:
            first_right = self._first_of_string(production.right)
            
            for terminal in first_right:
                if terminal != 'ε':
                    key = (production.left, terminal)
                    if key in self.parse_table:
                        raise ValueError(f"گرامر LL(1) نیست! تضاد در {key}")
                    self.parse_table[key] = production
            
            if 'ε' in first_right:
                for terminal in self.follow_sets[production.left]:
                    key = (production.left, terminal)
                    if key in self.parse_table:
                        raise ValueError(f"گرامر LL(1) نیست! تضاد در {key}")
                    self.parse_table[key] = production
    
    def print_first_follow(self):
        print("FIRST Sets:")
        for symbol in sorted(self.first_sets.keys()):
            print(f"FIRST({symbol}) = {self.first_sets[symbol]}")
        
        print("\nFOLLOW Sets:")
        for symbol in sorted(self.follow_sets.keys()):
            print(f"FOLLOW({symbol}) = {self.follow_sets[symbol]}")
    
    def print_parse_table(self):
        print("\nParse Table:")
        terminals = sorted(self.terminals | {'$'})
        non_terminals = sorted(self.non_terminals)
        
        header = "Non-Terminal".ljust(15)
        for terminal in terminals:
            header += terminal.ljust(20)
        print(header)
        print("-" * len(header))
        
        for nt in non_terminals:
            row = nt.ljust(15)
            for t in terminals:
                if (nt, t) in self.parse_table:
                    prod = self.parse_table[(nt, t)]
                    cell = f"{prod.left} -> {' '.join(prod.right)}"
                else:
                    cell = ""
                row += cell.ljust(20)
            print(row)

class ParseTreeNode:
    
    def __init__(self, symbol: str, is_terminal: bool = False):
        self.symbol = symbol
        self.is_terminal = is_terminal
        self.children: List['ParseTreeNode'] = []
        self.parent: Optional['ParseTreeNode'] = None
        self.position: Tuple[int, int] = (0, 0)  
        
    def add_child(self, child: 'ParseTreeNode'):
        child.parent = self
        self.children.append(child)
    
    def find_nodes_by_symbol(self, symbol: str) -> List['ParseTreeNode']:
        result = []
        if self.symbol == symbol:
            result.append(self)
        
        for child in self.children:
            result.extend(child.find_nodes_by_symbol(symbol))
        
        return result
    
    def get_text(self) -> str:
        if self.is_terminal and self.symbol != 'ε':
            return self.symbol
        
        text = ""
        for child in self.children:
            text += child.get_text()
        
        return text
    
    def print_tree(self, indent: int = 0):
        print("  " * indent + self.symbol)
        for child in self.children:
            child.print_tree(indent + 1)

class DPDA:
    
    def __init__(self):
        self.states: Set[str] = set()
        self.input_alphabet: Set[str] = set()
        self.stack_alphabet: Set[str] = set()
        self.transitions: Dict[Tuple[str, str, str], Tuple[str, List[str]]] = {}
        self.start_state: str = ""
        self.accept_states: Set[str] = set()
        self.initial_stack_symbol: str = ""
    
    def add_transition(self, from_state: str, input_symbol: str, stack_top: str, 
                      to_state: str, stack_push: List[str]):
        
        key = (from_state, input_symbol, stack_top)
        self.transitions[key] = (to_state, stack_push)
        
        self.states.add(from_state)
        self.states.add(to_state)
        
        if input_symbol != 'ε':
            self.input_alphabet.add(input_symbol)
        
        self.stack_alphabet.add(stack_top)
        for symbol in stack_push:
            if symbol != 'ε':
                self.stack_alphabet.add(symbol)
    
    def process_string(self, input_string: str) -> Tuple[bool, List[str]]:
        
        stack = [self.initial_stack_symbol]
        current_state = self.start_state
        input_index = 0
        applied_rules = []
        
        while input_index <= len(input_string):
            if input_index < len(input_string):
                current_input = input_string[input_index]
            else:
                current_input = '$'
            
            
            if not stack:
                break
            
            stack_top = stack[-1]
            
            
            transition_key = (current_state, current_input, stack_top)
            epsilon_key = (current_state, 'ε', stack_top)
            
            if transition_key in self.transitions:
                new_state, stack_push = self.transitions[transition_key]
                stack.pop()  
                
                
                for symbol in reversed(stack_push):
                    if symbol != 'ε':
                        stack.append(symbol)
                
                applied_rules.append(f"{stack_top} -> {' '.join(stack_push)}")
                current_state = new_state
                input_index += 1
                
            elif epsilon_key in self.transitions:
                new_state, stack_push = self.transitions[epsilon_key]
                stack.pop() 
                
                
                for symbol in reversed(stack_push):
                    if symbol != 'ε':
                        stack.append(symbol)
                
                applied_rules.append(f"{stack_top} -> {' '.join(stack_push)}")
                current_state = new_state
                
            else:
                break
        
        accepted = (input_index == len(input_string) + 1 and 
                   (not stack or (len(stack) == 1 and stack[0] in ['$', 'ε'])) and
                   current_state in self.accept_states)
        
        return accepted, applied_rules

def grammar_to_dpda(grammar: Grammar) -> DPDA:
    dpda = DPDA()
    
    dpda.start_state = "q0"
    dpda.accept_states = {"q1"}
    dpda.initial_stack_symbol = "$"
    dpda.input_alphabet = grammar.terminals.copy()
    dpda.stack_alphabet = grammar.non_terminals | grammar.terminals | {"$"}
    
    dpda.states = {"q0", "q1"}
    
    dpda.add_transition("q0", "ε", "$", "q0", [grammar.start_symbol, "$"])
    
    for (non_terminal, terminal), production in grammar.parse_table.items():
        dpda.add_transition("q0", "ε", non_terminal, "q0", production.right)
    
    for terminal in grammar.terminals:
        dpda.add_transition("q0", terminal, terminal, "q0", ["ε"])
    
    dpda.add_transition("q0", "$", "$", "q1", ["ε"])
    
    return dpda

def parse_string_with_tree(grammar: Grammar, input_string: str) -> Tuple[bool, Optional[ParseTreeNode], List[str]]:
    dpda = grammar_to_dpda(grammar)
    
    root = ParseTreeNode(grammar.start_symbol)
    node_stack = [root]
    
    stack = [dpda.initial_stack_symbol, grammar.start_symbol]
    input_index = 0
    applied_rules = []
    
    while input_index <= len(input_string) and len(stack) > 1:
        if input_index < len(input_string):
            current_input = input_string[input_index]
        else:
            current_input = '$'
        
        stack_top = stack[-1]
        
        if stack_top in grammar.non_terminals:
            if (stack_top, current_input) in grammar.parse_table:
                production = grammar.parse_table[(stack_top, current_input)]
                applied_rules.append(str(production))
                
                stack.pop()
                current_node = node_stack.pop()
                
                for symbol in reversed(production.right):
                    if symbol != 'ε':
                        stack.append(symbol)
                        child_node = ParseTreeNode(symbol, symbol in grammar.terminals)
                        current_node.add_child(child_node)
                        if symbol in grammar.non_terminals:
                            node_stack.append(child_node)
                    else:
                        epsilon_node = ParseTreeNode('ε', True)
                        current_node.add_child(epsilon_node)
                
                current_node.children.reverse()
                
                new_non_terminals = []
                for symbol in production.right:
                    if symbol in grammar.non_terminals:
                        for child in current_node.children:
                            if child.symbol == symbol and child not in new_non_terminals:
                                new_non_terminals.append(child)
                                break
                
                node_stack.extend(reversed(new_non_terminals))
                
            else:
                return False, None, applied_rules
                
        elif stack_top in grammar.terminals:
            if stack_top == current_input:
                stack.pop()
                input_index += 1
            else:
                return False, None, applied_rules
        else:
            return False, None, applied_rules
    
    success = (input_index == len(input_string) and len(stack) == 1 and stack[0] == '$')
    
    return success, root if success else None, applied_rules

def rename_symbol_in_tree(tree: ParseTreeNode, target_node: ParseTreeNode, 
                         old_name: str, new_name: str) -> str:
    
    def find_scope_boundary(node: ParseTreeNode) -> ParseTreeNode:
        current = node
        while current.parent:
            
            if current.parent.symbol in ['block', 'function', 'class', 'S']:
                return current.parent
            current = current.parent
        return tree  
    
    def rename_in_scope(node: ParseTreeNode, scope: ParseTreeNode, 
                       original_position: ParseTreeNode) -> List[ParseTreeNode]:
        renamed_nodes = []
        
        def traverse_and_rename(current: ParseTreeNode):
            if (current.symbol == old_name and 
                current.is_terminal and 
                is_same_variable_reference(current, original_position, scope)):
                current.symbol = new_name
                renamed_nodes.append(current)
            
            for child in current.children:
                traverse_and_rename(child)
        
        traverse_and_rename(scope)
        return renamed_nodes
    
    def is_same_variable_reference(node1: ParseTreeNode, node2: ParseTreeNode, 
                                  scope: ParseTreeNode) -> bool:
        
        def is_within_scope(node: ParseTreeNode, scope_boundary: ParseTreeNode) -> bool:
            current = node
            while current:
                if current == scope_boundary:
                    return True
                current = current.parent
            return False
        
        return (is_within_scope(node1, scope) and 
                is_within_scope(node2, scope) and
                node1.symbol == node2.symbol)
    
    scope = find_scope_boundary(target_node)
    
    renamed_nodes = rename_in_scope(tree, scope, target_node)
    
    modified_text = tree.get_text()
    
    print(f"تعداد {len(renamed_nodes)} مورد از '{old_name}' به '{new_name}' تغییر یافت.")
    return modified_text

def main():
    
    grammar = Grammar()
    
    # E -> T E'
    # E' -> + T E' | ε
    # T -> F T'
    # T' -> * F T' | ε  
    # F -> id | ( E )
    
    grammar.add_production("E", ["T", "E'"])
    grammar.add_production("E'", ["+", "T", "E'"])
    grammar.add_production("E'", ["ε"])
    grammar.add_production("T", ["F", "T'"])
    grammar.add_production("T'", ["*", "F", "T'"])
    grammar.add_production("T'", ["ε"])
    grammar.add_production("F", ["id"])
    grammar.add_production("F", ["(", "E", ")"])
    
    grammar.set_start_symbol("E")
    
    grammar._compute_first_sets()
    grammar._compute_follow_sets()
    grammar._build_parse_table()
    
    print("\n")
    for prod in grammar.productions:
        print(prod)
    
    grammar.print_first_follow()
    grammar.print_parse_table()
    
    print("\n")
    test_string = "id + id * id"
    print(f"input string: {test_string}")
    
    tokens = test_string.split()
    
    success, parse_tree, rules = parse_string_with_tree(grammar, tokens)
    
    if success:
        print("success")
        print(f"قوانین اعمال شده: {len(rules)} قانون")
        for i, rule in enumerate(rules, 1):
            print(f"  {i}. {rule}")
        
        parse_tree.print_tree()
        
        
        id_nodes = parse_tree.find_nodes_by_symbol('id')
        if id_nodes:
            target_node = id_nodes[0]  
            
            modified_text = rename_symbol_in_tree(parse_tree, target_node, 'id', 'variable')
            print(f"text: {modified_text}")
            
            print("\n after chnage name")
            parse_tree.print_tree()
    else:
        print("wrong")
        for rule in rules:
            print(f"  {rule}")

if __name__ == "__main__":
    main()

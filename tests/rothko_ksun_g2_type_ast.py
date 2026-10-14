"""Syntax-aware ownership checks for the G2 add_type candidate.

This deliberately accepts a narrow transaction protocol, not arbitrary C.
pycparser checks the actual function syntax; no C preprocessor or compiler runs.
The contract covers the insertion boundary and the staged bitmap/container
ownership. It does not prove SELinux policy semantics or runtime lifecycle.
"""

import re
from collections import Counter
from functools import lru_cache

from pycparser import c_ast, c_parser


_PREAMBLE = "typedef unsigned int bool; typedef unsigned int u32;\n"
_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*|\S', re.S)
_STAGED = {
    "new_type_attr_map_array", "new_type_val_to_struct",
    "new_val_to_name_types", "new_role_types", "key",
}


def _fail(message):
    raise RuntimeError("add_type AST ownership: " + message)


def _without_comments(source):
    """Apply C line splicing, then mask comments without changing literals."""
    # Translation phase two precedes comment recognition. Otherwise a continued
    # // comment could hide a failure guard from C while our parser sees it.
    source = re.sub(r"\\\r?\n", "", source)
    chars = list(source)
    i = 0
    quote = None
    while i < len(source):
        ch = source[i]
        if quote is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            i += 1
            continue
        if source.startswith("//", i):
            end = source.find("\n", i)
            if end < 0:
                end = len(source)
            for j in range(i, end):
                chars[j] = " "
            i = end
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            if end < 0:
                _fail("unterminated comment")
            end += 2
            for j in range(i, end):
                if chars[j] not in "\r\n":
                    chars[j] = " "
            i = end
            continue
        i += 1
    if quote is not None:
        _fail("unterminated quoted literal")
    return "".join(chars)


def _extract_add_type(source):
    masked = _without_comments(source)
    tokens = list(_TOKEN.finditer(masked))
    definitions = []
    for i, token in enumerate(tokens):
        if token.group() != "add_type" or i < 2:
            continue
        if [t.group() for t in tokens[i - 2:i]] != ["static", "bool"]:
            continue
        if i + 1 >= len(tokens) or tokens[i + 1].group() != "(":
            continue
        depth = 0
        j = i + 1
        while j < len(tokens):
            text = tokens[j].group()
            if text == "(":
                depth += 1
            elif text == ")":
                depth -= 1
                if not depth:
                    j += 1
                    break
            j += 1
        if j >= len(tokens) or tokens[j].group() != "{":
            continue  # A declaration is not the definition.
        depth = 0
        start = tokens[i - 2].start()
        while j < len(tokens):
            text = tokens[j].group()
            if text == "{":
                depth += 1
            elif text == "}":
                depth -= 1
                if not depth:
                    definitions.append(masked[start:tokens[j].end()])
                    break
            j += 1
        else:
            _fail("unterminated function body")
    if len(definitions) != 1:
        _fail("expected exactly one static bool add_type definition")
    if any(token.group() == "#" for token in _TOKEN.finditer(definitions[0])):
        _fail("preprocessor directives in add_type require explicit configuration")
    return definitions[0]


def _parse(body):
    try:
        ast = c_parser.CParser().parse(_PREAMBLE + body)
    except Exception as exc:
        _fail("C syntax could not be parsed: " + str(exc))
    functions = [node for node in ast.ext if isinstance(node, c_ast.FuncDef)]
    if len(functions) != 1:
        _fail("expected one parsed function")
    return functions[0]


def _walk(node):
    if node is None:
        return
    yield node
    for _, child in node.children():
        yield from _walk(child)


def _shape(node):
    if node is None:
        return None
    return (
        type(node).__name__,
        tuple((name, getattr(node, name)) for name in node.attr_names),
        tuple((name, _shape(child)) for name, child in node.children()),
    )


@lru_cache(maxsize=None)
def _statements(fragment):
    function = _parse("static bool contract(struct policydb *db) {" + fragment + "}")
    return tuple(function.body.block_items or [])


def _matches(actual, fragment):
    expected = _statements(fragment)
    return len(expected) == 1 and _shape(actual) == _shape(expected[0])


def _call_name(call):
    if not isinstance(call.name, c_ast.ID):
        _fail("indirect helper call is outside the checked protocol")
    return call.name.name


def _root_id(expression):
    while isinstance(expression, (c_ast.ArrayRef, c_ast.StructRef)):
        expression = expression.name
    if isinstance(expression, c_ast.UnaryOp) and expression.op == "*":
        return "*"
    return expression.name if isinstance(expression, c_ast.ID) else None


def _single_goto_abort(statement):
    if isinstance(statement, c_ast.Compound):
        items = statement.block_items or []
        return len(items) == 1 and _single_goto_abort(items[0])
    return isinstance(statement, c_ast.Goto) and statement.name == "abort"


def _allocation_guard(block, variable, allocator):
    matches = []
    for node in _walk(block):
        if not isinstance(node, c_ast.Compound):
            continue
        items = node.block_items or []
        for index, statement in enumerate(items):
            if not isinstance(statement, c_ast.Assignment):
                continue
            if not isinstance(statement.lvalue, c_ast.ID) or statement.lvalue.name != variable:
                continue
            if not isinstance(statement.rvalue, c_ast.FuncCall):
                continue
            if _call_name(statement.rvalue) != allocator:
                continue
            matches.append(statement)
            if index + 1 >= len(items):
                _fail(variable + " allocation lacks its failure guard")
            guard = items[index + 1]
            if (not isinstance(guard, c_ast.If) or guard.iffalse is not None
                    or not isinstance(guard.cond, c_ast.UnaryOp)
                    or guard.cond.op != "!" or not isinstance(guard.cond.expr, c_ast.ID)
                    or guard.cond.expr.name != variable
                    or not _single_goto_abort(guard.iftrue)):
                _fail(variable + " allocation must immediately branch to abort on NULL")
    if len(matches) != 1:
        _fail(variable + " must have exactly one staged " + allocator + " allocation")
    return matches[0]


# The staging grammar is intentionally complete. Counting helpers or finding a
# checked allocation anywhere in the tree does not prove that it executes
# before its owner is consumed. Exact top-level statement order rejects hidden
# conditional/loop paths and allocations moved after their first use.
_STAGING = r"""
    struct type_datum *type = symtab_search(&db->p_types, type_name);
    struct ebitmap *new_type_attr_map_array = NULL;
    struct type_datum **new_type_val_to_struct = NULL;
    char **new_val_to_name_types = NULL;
    struct ebitmap *new_role_types = NULL;
    struct ebitmap *old_type_attr_map_array;
    struct type_datum **old_type_val_to_struct;
    char **old_val_to_name_types;
    char *key = NULL;
    u32 value;
    u32 i;
    if (type) {
        pr_warn("Type %s already exists\n", type_name);
        return true;
    }
    value = db->p_types.nprim + 1;
    if (!value) {
        pr_err("add_type: type count overflow\n");
        return false;
    }
    type = kzalloc(sizeof(*type), GFP_KERNEL);
    if (!type)
        goto abort;
    type->primary = 1;
    type->value = value;
    type->attribute = attr;
    key = kstrdup(type_name, GFP_KERNEL);
    if (!key)
        goto abort;
    new_type_attr_map_array = kvcalloc(value, sizeof(*new_type_attr_map_array), GFP_KERNEL);
    if (!new_type_attr_map_array)
        goto abort;
    new_type_val_to_struct = kvcalloc(value, sizeof(*new_type_val_to_struct), GFP_KERNEL);
    if (!new_type_val_to_struct)
        goto abort;
    new_val_to_name_types = kvcalloc(value, sizeof(*new_val_to_name_types), GFP_KERNEL);
    if (!new_val_to_name_types)
        goto abort;
    if (db->p_types.nprim) {
        memcpy(new_type_attr_map_array, db->type_attr_map_array, db->p_types.nprim * sizeof(*new_type_attr_map_array));
        memcpy(new_type_val_to_struct, db->type_val_to_struct, db->p_types.nprim * sizeof(*new_type_val_to_struct));
        memcpy(new_val_to_name_types, db->sym_val_to_name[SYM_TYPES], db->p_types.nprim * sizeof(*new_val_to_name_types));
    }
    ebitmap_init(&new_type_attr_map_array[value - 1]);
    if (ebitmap_set_bit(&new_type_attr_map_array[value - 1], value - 1, 1))
        goto abort;
    new_type_val_to_struct[value - 1] = type;
    new_val_to_name_types[value - 1] = key;
    if (db->p_roles.nprim) {
        new_role_types = kvcalloc(db->p_roles.nprim, sizeof(*new_role_types), GFP_KERNEL);
        if (!new_role_types)
            goto abort;
    }
    for (i = 0; i < db->p_roles.nprim; ++i) {
        if (ebitmap_cpy(&new_role_types[i], &db->role_val_to_struct[i]->types) ||
            ebitmap_set_bit(&new_role_types[i], value - 1, 1))
            goto abort;
    }
"""


_SUCCESS = """
    old_type_attr_map_array = db->type_attr_map_array;
    old_type_val_to_struct = db->type_val_to_struct;
    old_val_to_name_types = db->sym_val_to_name[SYM_TYPES];
    db->type_attr_map_array = new_type_attr_map_array;
    db->type_val_to_struct = new_type_val_to_struct;
    db->sym_val_to_name[SYM_TYPES] = new_val_to_name_types;
    db->p_types.nprim = value;
    for (i = 0; i < db->p_roles.nprim; ++i) {
        ebitmap_destroy(&db->role_val_to_struct[i]->types);
        db->role_val_to_struct[i]->types = new_role_types[i];
        ebitmap_init(&new_role_types[i]);
    }
    kvfree(old_type_attr_map_array);
    kvfree(old_type_val_to_struct);
    kvfree(old_val_to_name_types);
    kvfree(new_role_types);
    return true;
"""

_ABORT = """
    if (new_role_types) {
        for (i = 0; i < db->p_roles.nprim; ++i)
            ebitmap_destroy(&new_role_types[i]);
    }
    if (new_type_attr_map_array)
        ebitmap_destroy(&new_type_attr_map_array[value - 1]);
    kvfree(new_role_types);
    kvfree(new_type_attr_map_array);
    kvfree(new_type_val_to_struct);
    kvfree(new_val_to_name_types);
    kfree(key);
    kfree(type);
    return false;
"""


def validate_add_type(sepolicy_source):
    """Raise RuntimeError unless add_type follows the staged ownership protocol."""
    function = _parse(_extract_add_type(sepolicy_source))
    expected_function = _parse(
        "static bool add_type(struct policydb *db, const char *type_name, bool attr) {}"
    )
    if _shape(function.decl) != _shape(expected_function.decl):
        _fail("function signature differs from the checked ownership protocol")
    items = function.body.block_items or []
    insert_calls = [node for node in _walk(function.body)
                    if isinstance(node, c_ast.FuncCall) and _call_name(node) == "symtab_insert"]
    if len(insert_calls) != 1:
        _fail("expected one checked symbol-table insertion")
    boundaries = [index for index, node in enumerate(items)
                  if isinstance(node, c_ast.If) and node.cond is insert_calls[0]]
    if len(boundaries) != 1:
        _fail("insertion status must be checked by a top-level if")
    boundary = boundaries[0]
    guard = items[boundary]
    if (not _matches(guard.cond, "symtab_insert(&db->p_types, key, type);")
            or guard.iffalse is not None or not _single_goto_abort(guard.iftrue)):
        _fail("failed insertion must retain staged ownership and go directly to abort")
    labels = [node for node in _walk(function.body) if isinstance(node, c_ast.Label)]
    if len(labels) != 1 or labels[0].name != "abort" or labels[0] not in items:
        _fail("expected one top-level abort label")
    abort_index = items.index(labels[0])
    if abort_index <= boundary:
        _fail("abort region must follow the successful publication region")

    # Check every node after insertion, including the gap before publication.
    # The exact ownership grammar then prevents nested control-flow escapes or
    # assignments to unrelated live policy fields even for nonfallible calls.
    success = items[boundary + 1:abort_index]
    for statement in success:
        for node in _walk(statement):
            if isinstance(node, c_ast.FuncCall) and _call_name(node) not in {
                "ebitmap_destroy", "ebitmap_init", "kvfree",
            }:
                _fail("fallible or unknown helper after insertion: " + _call_name(node))
            if isinstance(node, c_ast.Goto):
                _fail("success region can jump after ownership transfer")
            if isinstance(node, c_ast.Return) and not _matches(node, "return true;"):
                _fail("success region contains a failure return")
    if tuple(_shape(node) for node in success) != tuple(_shape(node) for node in _statements(_SUCCESS)):
        _fail("success region must publish once, transfer staged roles, free only containers, and return true")

    # A C label owns its first statement; it is not a separate empty marker.
    abort = [labels[0].stmt] + items[abort_index + 1:]
    if not abort or not isinstance(abort[0], c_ast.FuncCall) or _call_name(abort[0]) != "pr_err":
        _fail("abort diagnostic must be followed by staged-object cleanup")
    diagnostic_args = abort[0].args.exprs if abort[0].args is not None else []
    if (len(diagnostic_args) != 2 or not isinstance(diagnostic_args[0], c_ast.Constant)
            or diagnostic_args[0].type != "string" or not isinstance(diagnostic_args[1], c_ast.ID)
            or diagnostic_args[1].name != "type_name"):
        _fail("abort diagnostic has unchecked side effects")
    if tuple(_shape(node) for node in abort[1:]) != tuple(_shape(node) for node in _statements(_ABORT)):
        _fail("abort must destroy only staged role copies and the new last bitmap, then free staged objects")

    if tuple(_shape(node) for node in items[:boundary]) != tuple(
            _shape(node) for node in _statements(_STAGING)):
        _fail("staging must follow the complete top-level allocation, guard, and ownership order")

    staging = c_ast.Compound(items[:boundary])
    declarations = {node.name: node for node in items[:boundary] if isinstance(node, c_ast.Decl)}
    expected_declarations = _STAGED | {
        "type", "old_type_attr_map_array", "old_type_val_to_struct",
        "old_val_to_name_types", "value", "i",
    }
    all_declarations = [node for node in _walk(staging) if isinstance(node, c_ast.Decl)]
    if set(declarations) != expected_declarations or len(all_declarations) != len(expected_declarations):
        _fail("staging declares an unexpected ownership alias")
    for name in expected_declarations - _STAGED - {"type"}:
        if declarations[name].init is not None:
            _fail(name + " must not acquire ownership through an initializer")
    for name in _STAGED:
        declaration = declarations.get(name)
        if declaration is None or not isinstance(declaration.init, c_ast.ID) or declaration.init.name != "NULL":
            _fail(name + " must start as NULL for partial-allocation cleanup")
    type_decl = declarations.get("type")
    if type_decl is None or not _matches(type_decl.init, "symtab_search(&db->p_types, type_name);"):
        _fail("existing type lookup must precede staged allocation")

    allocations = {
        "type": ("kzalloc", "type = kzalloc(sizeof(*type), GFP_KERNEL);"),
        "key": ("kstrdup", "key = kstrdup(type_name, GFP_KERNEL);"),
        "new_type_attr_map_array": ("kvcalloc", "new_type_attr_map_array = kvcalloc(value, sizeof(*new_type_attr_map_array), GFP_KERNEL);"),
        "new_type_val_to_struct": ("kvcalloc", "new_type_val_to_struct = kvcalloc(value, sizeof(*new_type_val_to_struct), GFP_KERNEL);"),
        "new_val_to_name_types": ("kvcalloc", "new_val_to_name_types = kvcalloc(value, sizeof(*new_val_to_name_types), GFP_KERNEL);"),
        "new_role_types": ("kvcalloc", "new_role_types = kvcalloc(db->p_roles.nprim, sizeof(*new_role_types), GFP_KERNEL);"),
    }
    allocation_nodes = {}
    for name, (allocator, expected) in allocations.items():
        allocation_nodes[name] = _allocation_guard(staging, name, allocator)
        if not _matches(allocation_nodes[name], expected):
            _fail(name + " allocation must preserve its checked size and zero initialization")

    known_calls = {
        "symtab_search", "pr_warn", "pr_err", "kzalloc", "kstrdup", "kvcalloc",
        "memcpy", "ebitmap_init", "ebitmap_set_bit", "ebitmap_cpy",
    }
    for node in _walk(staging):
        if isinstance(node, c_ast.FuncCall) and _call_name(node) not in known_calls:
            _fail("unknown helper during staging: " + _call_name(node))
        if isinstance(node, c_ast.Assignment):
            if _root_id(node.lvalue) not in _STAGED | {"type", "value", "i"}:
                _fail("staging writes a live or untracked object")
        if isinstance(node, c_ast.UnaryOp) and node.op in {"p++", "++", "p--", "--"}:
            if not isinstance(node.expr, c_ast.ID) or node.expr.name != "i":
                _fail("staging modifies an untracked counter or live object")
        if isinstance(node, c_ast.Goto) and node.name != "abort":
            _fail("staging has an unchecked exit target")
    expected_calls = Counter({
        "symtab_search": 1, "pr_warn": 1, "pr_err": 1, "kzalloc": 1,
        "kstrdup": 1, "kvcalloc": 4, "memcpy": 3, "ebitmap_init": 1,
        "ebitmap_set_bit": 2, "ebitmap_cpy": 1,
    })
    actual_calls = Counter(_call_name(node) for node in _walk(staging)
                           if isinstance(node, c_ast.FuncCall))
    if actual_calls != expected_calls:
        _fail("staging contains an extra helper or an unchecked bitmap operation")
    allowed_writes = [
        *(expected for _, expected in allocations.values()),
        "value = db->p_types.nprim + 1;", "type->primary = 1;",
        "type->value = value;", "type->attribute = attr;",
        "new_type_val_to_struct[value - 1] = type;",
        "new_val_to_name_types[value - 1] = key;", "i = 0;",
    ]
    assignments = [node for node in _walk(staging) if isinstance(node, c_ast.Assignment)]
    for fragment in allowed_writes:
        if sum(_matches(node, fragment) for node in assignments) != 1:
            _fail("staging changes or aliases tracked ownership: " + fragment)
    if len(assignments) != len(allowed_writes):
        _fail("staging reassigns an owner or introduces a live-pointer alias")

    required = [
        "value = db->p_types.nprim + 1;",
        "type->primary = 1;", "type->value = value;", "type->attribute = attr;",
        "if (db->p_types.nprim) { memcpy(new_type_attr_map_array, db->type_attr_map_array, db->p_types.nprim * sizeof(*new_type_attr_map_array)); memcpy(new_type_val_to_struct, db->type_val_to_struct, db->p_types.nprim * sizeof(*new_type_val_to_struct)); memcpy(new_val_to_name_types, db->sym_val_to_name[SYM_TYPES], db->p_types.nprim * sizeof(*new_val_to_name_types)); }",
        "ebitmap_init(&new_type_attr_map_array[value - 1]);",
        "if (ebitmap_set_bit(&new_type_attr_map_array[value - 1], value - 1, 1)) goto abort;",
        "new_type_val_to_struct[value - 1] = type;",
        "new_val_to_name_types[value - 1] = key;",
        "if (db->p_roles.nprim) { new_role_types = kvcalloc(db->p_roles.nprim, sizeof(*new_role_types), GFP_KERNEL); if (!new_role_types) goto abort; }",
        "for (i = 0; i < db->p_roles.nprim; ++i) { if (ebitmap_cpy(&new_role_types[i], &db->role_val_to_struct[i]->types) || ebitmap_set_bit(&new_role_types[i], value - 1, 1)) goto abort; }",
    ]
    positions = []
    for fragment in required:
        matches = [index for index, node in enumerate(items[:boundary]) if _matches(node, fragment)]
        if len(matches) != 1:
            _fail("required staging step missing, repeated, or changed: " + fragment.split(";")[0])
        positions.append(matches[0])
    if positions != sorted(positions):
        _fail("staged initialization and bitmap checks are out of ownership order")
    for name in ("new_type_attr_map_array", "new_type_val_to_struct", "new_val_to_name_types"):
        if items.index(allocation_nodes[name]) >= positions[4]:
            _fail(name + " must be allocated and checked before shallow copying")

    # Before the first allocation, only a successful duplicate lookup or a
    # failed count-overflow check may return; neither may mutate/free the db.
    executable = [node for node in items[:boundary] if not isinstance(node, c_ast.Decl)]
    if len(executable) < 4 or not isinstance(executable[0], c_ast.If):
        _fail("missing duplicate-type early return")
    duplicate = executable[0]
    duplicate_items = duplicate.iftrue.block_items if isinstance(duplicate.iftrue, c_ast.Compound) else []
    if (not isinstance(duplicate.cond, c_ast.ID) or duplicate.cond.name != "type"
            or duplicate.iffalse is not None or len(duplicate_items) != 2
            or not isinstance(duplicate_items[0], c_ast.FuncCall)
            or _call_name(duplicate_items[0]) != "pr_warn"
            or not _matches(duplicate_items[1], "return true;")):
        _fail("existing type must return successfully before staged allocation")
    duplicate_args = duplicate_items[0].args.exprs if duplicate_items[0].args else []
    if (len(duplicate_args) != 2 or not isinstance(duplicate_args[0], c_ast.Constant)
            or duplicate_args[0].type != "string" or not isinstance(duplicate_args[1], c_ast.ID)
            or duplicate_args[1].name != "type_name"):
        _fail("duplicate diagnostic has unchecked side effects")
    if not _matches(executable[1], "value = db->p_types.nprim + 1;"):
        _fail("type count must be staged before overflow check")
    overflow = executable[2]
    overflow_items = overflow.iftrue.block_items if isinstance(overflow, c_ast.If) and isinstance(overflow.iftrue, c_ast.Compound) else []
    if (not isinstance(overflow, c_ast.If) or overflow.iffalse is not None
            or not _matches(overflow.cond, "!value;") or len(overflow_items) != 2
            or not isinstance(overflow_items[0], c_ast.FuncCall)
            or _call_name(overflow_items[0]) != "pr_err"
            or not _matches(overflow_items[1], "return false;")):
        _fail("count overflow must fail before any staged ownership exists")
    overflow_args = overflow_items[0].args.exprs if overflow_items[0].args else []
    if len(overflow_args) != 1 or not isinstance(overflow_args[0], c_ast.Constant) or overflow_args[0].type != "string":
        _fail("overflow diagnostic has unchecked side effects")
    if executable[3] is not allocation_nodes["type"]:
        _fail("a newly allocated type must replace the lookup result before any type writes")
    returns = [node for node in _walk(staging) if isinstance(node, c_ast.Return)]
    if returns != [duplicate_items[1], overflow_items[1]]:
        _fail("staging contains an unchecked early return")

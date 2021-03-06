from SCons.Script import *
from SCons import Action


def exists(env):
    """
    The exists() function should return a true value if the tool is
    available. Tools in the toolpath are used before any of the built-in ones
    """
    return True


def emit_check(target, source, env):
    variant_dir = env.get('CHECK_VARIANT_DIR', 'build_test')
    test_dir = env.get('CHECK_TEST_DIR', 'test')
    src_dir = env.get('CHECK_SRC_DIR', 'src')
    lib_dir = env.get('CHECK_LIB_DIR', 'lib')
    exec_name = env.get('CHECK_EXEC_NAME', 'check_exec')

    # Create a Variant dir for each of the possibly used directories
    env.VariantDir(os.path.join(variant_dir, test_dir),
                   test_dir,
                   duplicate=0)
    env.VariantDir(os.path.join(variant_dir, src_dir),
                   src_dir,
                   duplicate=0)
    env.VariantDir(os.path.join(variant_dir, lib_dir),
                   lib_dir,
                   duplicate=0)

    # TODO: Find out why the emitted sources are not visible in build_check
    new_sources = [os.path.join(variant_dir, s.get_path()) for s in source]

    env.Clean(target, variant_dir)
    env.Clean(target, exec_name)
    return target, new_sources


def build_check_str(target, source, env):
    return "Building Check unit tests for target {}".format(
        target[0].get_path())


def build_check(target, source, env):
    target_dir = os.path.dirname(target[0].get_path())
    target_name = os.path.basename(target[0].get_path())
    exec_name = os.path.join(target_dir, 'check_exec')
    extra_defines = env.get('CHECK_EXTRA_DEFINES', [])
    single_file_opts = env.get('CHECK_SINGLE_FILE_OPTIONS', {})
    linker_exec = env.get('linker_exec', env['CC'])
    variant_dir = env.get('CHECK_VARIANT_DIR', 'build_test')

    local_env = env.Clone()
    local_env.Append(LIBS='check')
    defines = local_env['CPPDEFINES']
    local_env.Append(CCFLAGS="-g")
    local_env.Replace(CPPDEFINES=defines)
    local_env.Append(CPPDEFINES=extra_defines)
    # RF_UNIT_TESTS is only defined for tests
    local_env.Append(CPPDEFINES=['RF_UNIT_TESTS'])
    new_source = []
    special_care_objects = []
    for n in source:
        path = n.get_path()
        tail_path = ""
        while os.path.dirname(path) != '':
            (head, tail) = os.path.split(path)
            tail_path = os.path.join(tail, tail_path)
            path = head
        new_path = os.path.join(path, variant_dir, tail_path.rstrip('/'))
        filename = os.path.basename(tail_path.rstrip('/'))
        if filename in single_file_opts:
            special_care_objects.append(local_env.Object(
                new_path, CCFLAGS=single_file_opts[filename]
            ))
        else:
            new_source.append(new_path)

    objects = local_env.Object(new_source)
    check_exec = local_env.Program(exec_name, [objects, special_care_objects],
                                   CC=linker_exec)

    # if we got specific case or suite modify the environment
    # and also switch to verbose output
    if local_env['TEST_CASE'] != '':
        local_env.Append(ENV={'CK_RUN_CASE': local_env['TEST_CASE']})
        local_env['TEST_OUTPUT'] = 'CK_VERBOSE'
    if local_env['TEST_SUITE'] != '':
        local_env.Append(ENV={'CK_RUN_SUITE': local_env['TEST_SUITE']})
        local_env['TEST_OUTPUT'] = 'CK_VERBOSE'

    # run the tests
    run = local_env.Command(
        target='run', source=check_exec,
        action='{} {} {}'.format(
            exec_name,
            local_env['TEST_OUTPUT'],
            local_env['TEST_FORK']))
    Alias(target_name, run)

    if local_env['has_valgrind'] and local_env['TEST_VIA_VALGRIND']:
        valgrind_cmd = [
            "valgrind",
            "--tool=memcheck",
            "--leak-check=yes",
            "--track-origins=yes",
            "--show-reachable=yes",
            "--num-callers=20",
            "--track-fds=yes"
        ]
        run_val = local_env.Command(
            target='run_val',
            source=check_exec,
            action=(
                " ".join(valgrind_cmd) +
                " {} {} {}".format(
                    exec_name,
                    local_env['TEST_OUTPUT'],
                    False)))
        Alias(target_name, run_val)
    # success
    return 0


def generate(env, **kw):
    """
    The generate() function modifies the passed-in environment to set up
    variables so that the tool can be executed; it may use any keyword
    arguments that the user supplies (see below) to vary its initialization.
    """
    bld = Builder(action=Action.Action(build_check, build_check_str),
                  emitter=emit_check)
    env.Append(BUILDERS={'Check': bld})
    return True

from pathlib import Path
import sys

root = Path(sys.argv[1])
path = root / 'src/win32_window.c'
text = path.read_text(encoding='utf-8')
lookup = '''// Umaipoe modification: attached input queues can expose another process's HWND.
static _GLFWwindow* findOwnedActiveWindow(HWND handle)
{
    _GLFWwindow* window = _glfw.windowListHead;
    while (window && window->win32.handle != handle)
        window = window->next;
    return window;
}

'''
signature = 'void _glfwPollEventsWin32(void)'
text = text.replace(signature, lookup + signature, 1)
start = text.index(signature)
end = text.index('void _glfwWaitEventsWin32', start)
body = text[start:end]
old = 'window = GetPropW(handle, L"GLFW");'
assert body.count(old) == 1
body = body.replace(old, 'window = findOwnedActiveWindow(handle);')
path.write_text(text[:start] + body + text[end:], encoding='utf-8')
test = '''#include <stdio.h>
typedef void* HWND;
typedef struct Window { struct Window* next; struct { HWND handle; } win32; } _GLFWwindow;
static struct { _GLFWwindow* windowListHead; } _glfw;
''' + lookup + '''
int main(void) {
    _GLFWwindow b = {0, {(HWND)2}}, a = {&b, {(HWND)1}};
    _glfw.windowListHead = &a;
    if (findOwnedActiveWindow((HWND)1) != &a) return 1;
    if (findOwnedActiveWindow((HWND)2) != &b) return 2;
    if (findOwnedActiveWindow((HWND)3) != 0) return 3;
    if (findOwnedActiveWindow(0) != 0) return 4;
    _glfw.windowListHead = 0;
    if (findOwnedActiveWindow((HWND)1) != 0) return 5;
    puts("PASS owned windows, foreign handle, null handle and empty window list");
    return 0;
}
'''
(root / 'ownership-test.c').write_text(test, encoding='utf-8')
print('Patched active-window lookup without dereferencing foreign GLFW properties.')

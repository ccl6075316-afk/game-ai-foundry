#import <AppKit/AppKit.h>
#import <objc/runtime.h>
#include <stdint.h>

// Godot 4.7 GDExtension initialization ABI used by this window-only helper.
typedef uint8_t GDExtensionBool;
typedef void *GDExtensionClassLibraryPtr;
typedef void (*GDExtensionInterfaceFunctionPtr)(void);
typedef GDExtensionInterfaceFunctionPtr (*GDExtensionInterfaceGetProcAddress)(const char *);
typedef enum {
    GDEXTENSION_INITIALIZATION_CORE,
    GDEXTENSION_INITIALIZATION_SERVERS,
    GDEXTENSION_INITIALIZATION_SCENE,
    GDEXTENSION_INITIALIZATION_EDITOR
} GDExtensionInitializationLevel;
typedef struct {
    GDExtensionInitializationLevel minimum_initialization_level;
    void *userdata;
    void (*initialize)(void *, GDExtensionInitializationLevel);
    void (*deinitialize)(void *, GDExtensionInitializationLevel);
} GDExtensionInitialization;

static BOOL placingPreview = YES;
static void (*originalActivate)(id, SEL);
static void (*originalActivateIgnoringOthers)(id, SEL, BOOL);
static BOOL (*originalActivateWithOptions)(id, SEL, NSApplicationActivationOptions);
static void (*originalMakeKeyAndOrderFront)(id, SEL, id);

static void activate_after_placement(id receiver, SEL selector) {
    if (!placingPreview) {
        originalActivate(receiver, selector);
    }
}

static void activate_ignoring_others_after_placement(id receiver, SEL selector, BOOL flag) {
    if (!placingPreview) {
        originalActivateIgnoringOthers(receiver, selector, flag);
    }
}

static BOOL activate_running_app_after_placement(id receiver, SEL selector, NSApplicationActivationOptions options) {
    if (placingPreview && [(NSRunningApplication *)receiver processIdentifier] == getpid()) {
        return NO;
    }
    return originalActivateWithOptions(receiver, selector, options);
}

static void make_key_after_placement(id receiver, SEL selector, id sender) {
    if (placingPreview) {
        [(NSWindow *)receiver orderFront:sender];
    } else {
        originalMakeKeyAndOrderFront(receiver, selector, sender);
    }
}

__attribute__((constructor))
static void prevent_activation_during_preview_startup(void) {
    if (getenv("FOUNDRY_BACKGROUND_PREVIEW") == NULL) {
        placingPreview = NO;
        return;
    }
    Method activate = class_getInstanceMethod(NSApplication.class, @selector(activate));
    if (activate != NULL) {
        originalActivate = (void (*)(id, SEL))method_setImplementation(activate, (IMP)activate_after_placement);
    }
    Method ignore = class_getInstanceMethod(NSApplication.class, @selector(activateIgnoringOtherApps:));
    originalActivateIgnoringOthers = (void (*)(id, SEL, BOOL))method_setImplementation(
        ignore, (IMP)activate_ignoring_others_after_placement
    );
    Method options = class_getInstanceMethod(NSRunningApplication.class, @selector(activateWithOptions:));
    originalActivateWithOptions = (BOOL (*)(id, SEL, NSApplicationActivationOptions))method_setImplementation(
        options, (IMP)activate_running_app_after_placement
    );
    Method keyWindow = class_getInstanceMethod(NSWindow.class, @selector(makeKeyAndOrderFront:));
    originalMakeKeyAndOrderFront = (void (*)(id, SEL, id))method_setImplementation(
        keyWindow, (IMP)make_key_after_placement
    );
}

static void initialize_preview(void *userdata, GDExtensionInitializationLevel level) {
    if (level != GDEXTENSION_INITIALIZATION_SCENE) {
        return;
    }
    [NSApp unhideWithoutActivation];
    // Order the real window after AppKit has attached it to the active Space.
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 300 * NSEC_PER_MSEC), dispatch_get_main_queue(), ^{
        for (NSWindow *window in NSApp.windows) {
            if (window.visible && window.level == NSNormalWindowLevel &&
                    [window.title containsString:@"潮汐馆 · 缸体定制原型"]) {
                [window orderBack:nil];
            }
        }
        placingPreview = NO;
    });
}

static void deinitialize_preview(void *userdata, GDExtensionInitializationLevel level) {}

GDExtensionBool initialize_order_preview(GDExtensionInterfaceGetProcAddress get_proc_address,
                                        GDExtensionClassLibraryPtr library,
                                        GDExtensionInitialization *initialization) {
    initialization->minimum_initialization_level = GDEXTENSION_INITIALIZATION_SCENE;
    initialization->userdata = NULL;
    initialization->initialize = initialize_preview;
    initialization->deinitialize = deinitialize_preview;
    return 1;
}

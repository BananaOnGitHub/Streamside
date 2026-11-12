#import <UIKit/UIKit.h>

/* Owned UIKit boundary; never invokes a private donor Swift method. Main thread. */
BOOL SSNInstallWindowOwnership(UIWindow *window, UIViewController *root);

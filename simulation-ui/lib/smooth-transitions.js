// Smooth transition utilities for the simulation UI

/**
 * Interpolates between two user states for smooth transitions
 * @param {Array} oldUsers - Previous user states
 * @param {Array} newUsers - New user states
 * @param {number} progress - Progress from 0 to 1
 * @returns {Array} Interpolated user states
 */
export const interpolateUsers = (oldUsers, newUsers, progress) => {
  if (!oldUsers || !newUsers || progress >= 1) {
    return newUsers;
  }
  
  if (progress <= 0) {
    return oldUsers;
  }
  
  // Create a map of old users for quick lookup
  const oldUserMap = new Map(oldUsers.map(user => [user.id, user]));
  
  return newUsers.map(newUser => {
    const oldUser = oldUserMap.get(newUser.id);
    
    if (!oldUser) {
      // New user - animate in
      return {
        ...newUser,
        opacity: progress,
        scale: 0.8 + (0.2 * progress)
      };
    }
    
    // Interpolate position
    const x = oldUser.x + (newUser.x - oldUser.x) * progress;
    const y = oldUser.y + (newUser.y - oldUser.y) * progress;
    
    return {
      ...newUser,
      x,
      y,
      opacity: 1,
      scale: 1
    };
  });
};

/**
 * Easing function for smooth animations
 * @param {number} t - Progress from 0 to 1
 * @returns {number} Eased progress
 */
export const easeInOutCubic = (t) => {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
};

/**
 * Creates a smooth transition manager
 * @param {Function} onUpdate - Callback for animation updates
 * @param {number} duration - Duration in milliseconds
 * @returns {Object} Transition manager with start method
 */
export const createTransitionManager = (onUpdate, duration = 300) => {
  let animationFrame = null;
  let startTime = null;
  
  const animate = (currentTime) => {
    if (!startTime) startTime = currentTime;
    
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easedProgress = easeInOutCubic(progress);
    
    onUpdate(easedProgress);
    
    if (progress < 1) {
      animationFrame = requestAnimationFrame(animate);
    } else {
      animationFrame = null;
      startTime = null;
    }
  };
  
  return {
    start: (oldState, newState) => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
      startTime = null;
      animationFrame = requestAnimationFrame(animate);
    },
    
    stop: () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
        animationFrame = null;
        startTime = null;
      }
    }
  };
};

/**
 * Debounce function for smooth state updates
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

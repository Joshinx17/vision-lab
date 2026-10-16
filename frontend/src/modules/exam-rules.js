export class ExamRules {
  constructor() { this.warnings = []; this.absentSince = null; this.lastWarning = -Infinity; }
  evaluate(faces, now) {
    let reason = null;
    if (!faces.length) {
      this.absentSince ??= now;
      if (now - this.absentSince > 3000) reason = 'NO FACE DETECTED';
    } else {
      this.absentSince = null;
      if (faces.length > 1) reason = 'MULTIPLE FACES';
      else if (faces[0].offset > .35) reason = 'LOOKING AWAY';
      else {
        const expression = ['angry', 'fearful', 'disgusted', 'sad'].find(key => faces[0].expressions[key] > .4);
        if (expression) reason = `EXPRESSION RULE: ${expression.toUpperCase()}`;
      }
    }
    let issued = false;
    if (reason && now - this.lastWarning > 5000 && this.warnings.length < 3) {
      this.warnings.push({ reason, timestamp: now }); this.lastWarning = now;
      if (!faces.length) this.absentSince = null;
      issued = true;
    }
    return { warnings: [...this.warnings], terminated: this.warnings.length >= 3, issued };
  }
}

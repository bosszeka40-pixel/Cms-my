# CMS Work Checklist

## Per-function closure
- [ ] UI/template exists and is the active template
- [ ] JavaScript/event handlers are connected
- [ ] API endpoint exists and matches frontend contract
- [ ] Router/controller reaches the correct service
- [ ] Service/domain logic is implemented once (no duplicate source of truth)
- [ ] DB/storage dependencies are verified
- [ ] External integration dependencies are verified when applicable
- [ ] Success and error responses reach the UI correctly
- [ ] UI state updates correctly
- [ ] Mobile/light/dark design is consistent
- [ ] Integration/regression test passes
- [ ] Branch marked DONE in TREE.md and PROJECT_STATUS.md

## Cleanup
- [ ] Suspicious code marked CANDIDATE before deletion
- [ ] All references searched
- [ ] Tests checked
- [ ] Moved if required elsewhere
- [ ] Deleted only after dependency check
